import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit
from rest_framework import generics

from middleware.rate_limiting import post_creation_ratelimit
from notifications.utils import send_notification

from .forms import CommentForm, PostForm
from .models import Bookmark, Hashtag, Post, Reaction, Story
from .serializers import PostSerializer
from .utils import visible_post_queryset

logger = logging.getLogger(__name__)


def landing_page(request):
    if request.user.is_authenticated:
        return redirect('posts:post_list')
    return render(request, 'posts/landing.html')

@login_required
def post_list(request):
    posts = visible_post_queryset(request.user).select_related(
        'author', 'author__profile'
    ).order_by('-created_at')
    paginator = Paginator(posts, 10)

    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'posts/post_list.html', {'page_obj': page_obj})

@login_required
@post_creation_ratelimit
def post_create(request):
    """إنشاء منشور جديد"""
    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                post = form.save(commit=False)
                post.author = request.user
                post.save()
                messages.success(request, _('تم إنشاء المنشور بنجاح!'))
                return redirect('posts:post_list')
            except ValidationError as e:
                messages.error(request, _('خطأ في التحقق من المنشور: ') + str(e))
            except Exception as e:
                logger.error(f"Error creating post: {str(e)}")
                messages.error(request, _('حدث خطأ أثناء إنشاء المنشور.'))
        else:
            # Handle form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PostForm()
    return render(request, 'posts/post_create.html', {'form': form})

@login_required
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def post_edit(request, post_id):
    post = get_object_or_404(Post.objects.select_related('author'), id=post_id)

    if post.author != request.user:
        messages.error(request, _('لا يمكنك تعديل منشور شخص آخر.'))
        return redirect('posts:post_detail', post_id=post.id)

    if request.method == 'POST':
        form = PostForm(request.POST, request.FILES, instance=post)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, _('تم تحديث المنشور بنجاح!'))
                return redirect('posts:post_detail', post_id=post.id)
            except ValidationError as e:
                messages.error(request, _('خطأ في التحقق من المنشور: ') + str(e))
            except Exception as e:
                logger.error(f"Error updating post: {str(e)}")
                messages.error(request, _('حدث خطأ أثناء تحديث المنشور.'))
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = PostForm(instance=post)
    return render(request, 'posts/post_edit.html', {'form': form, 'post': post})


@login_required
def post_detail(request, post_id):
    """عرض تفاصيل منشور معين"""
    post = get_object_or_404(Post.objects.select_related('author'), id=post_id)
    comments = post.comments.select_related('author').all().order_by('-created_at')

    if request.method == 'POST':
        comment_form = CommentForm(request.POST)
        if comment_form.is_valid():
            try:
                comment = comment_form.save(commit=False)
                comment.post = post
                comment.author = request.user
                comment.save()
                messages.success(request, _('تم إضافة تعليقك بنجاح!'))
                # Send notification
                if request.user != post.author:
                    send_notification(
                        post.author,
                        f'{request.user.username} علق على منشورك',
                        'comment',
                        related_user=request.user,
                        related_post=post
                    )
                return redirect('posts:post_detail', post_id=post.id)
            except ValidationError as e:
                messages.error(request, _('خطأ في التحقق من التعليق: ') + str(e))
            except Exception as e:
                logger.error(f"Error saving comment: {str(e)}")
                messages.error(request, _('حدث خطأ أثناء حفظ التعليق.'))
        else:
            for field, errors in comment_form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        comment_form = CommentForm()

    return render(request, 'posts/post_detail.html', {
        'post': post,
        'comments': comments,
        'comment_form': comment_form
    })

@login_required
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def post_delete(request, post_id):
    post = get_object_or_404(Post, id=post_id, author=request.user)
    if request.method == 'POST':
        post.delete()
        messages.success(request, _('تم حذف المنشور بنجاح!'))
        return redirect('posts:post_list')
    return render(request, 'posts/post_confirm_delete.html', {'post': post})

@login_required
@ratelimit(key='user', rate='10/m', method='POST', block=True)
def react_to_post(request, post_id):
    try:
        post = get_object_or_404(Post.objects.select_related('author'), id=post_id)
        reaction_type = request.POST.get('reaction', 'like')

        valid_reactions = [choice[0] for choice in Reaction.REACTION_CHOICES]
        if reaction_type not in valid_reactions:
            return JsonResponse({
                'status': 'error',
                'message': _('نوع التفاعل غير صالح.')
            }, status=400)

        reaction, created = Reaction.objects.get_or_create(
            post=post,
            user=request.user,
            defaults={'reaction_type': reaction_type}
        )

        if not created:
            if reaction.reaction_type == reaction_type:
                reaction.delete()
                reacted = False
                reaction_type = None
            else:
                reaction.reaction_type = reaction_type
                reaction.save()
                reacted = True
                if request.user != post.author:
                    send_notification(
                        post.author,
                        f'{request.user.username} تفاعل على منشورك بـ {reaction_type}',
                        'reaction',
                        related_user=request.user,
                        related_post=post
                    )
        else:
            reacted = True
            if request.user != post.author:
                send_notification(
                    post.author,
                    f'{request.user.username} تفاعل على منشورك بـ {reaction_type}',
                    'reaction',
                    related_user=request.user,
                    related_post=post
                )

        return JsonResponse({
            'status': 'success',
            'reacted': reacted,
            'reaction_type': reaction_type,
            'total_reactions': post.total_reactions()
        })
    except Exception as e:
        logger.error(f"Error processing reaction: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': _('حدث خطأ أثناء معالجة التفاعل.')
        }, status=500)

@login_required
def hashtag_posts(request, hashtag_name):
    """عرض المنشورات حسب الهاشتاج"""
    hashtag = get_object_or_404(Hashtag, name=hashtag_name)
    posts = visible_post_queryset(request.user).filter(
        hashtags=hashtag
    ).select_related('author').order_by('-created_at')
    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'posts/hashtag_posts.html', {'hashtag': hashtag, 'page_obj': page_obj})

@login_required
def trending_hashtags(request):
    from django.core.cache import cache
    from django.db.models import Count
    hashtags = cache.get('trending_hashtags')
    if hashtags is None:
        hashtags = Hashtag.objects.annotate(post_count=Count('posts')).order_by('-post_count')[:10]
        cache.set('trending_hashtags', hashtags, 300)  # Cache for 5 minutes
    return render(request, 'posts/trending_hashtags.html', {'hashtags': hashtags})

@login_required
def stories_list(request):
    """عرض القصص النشطة"""
    stories = Story.objects.select_related('author').filter(expires_at__gt=timezone.now()).order_by('-created_at')
    return render(request, 'posts/stories_list.html', {'stories': stories})

@login_required
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def create_story(request):
    """إنشاء قصة جديدة"""
    if request.method == 'POST':
        content = request.POST.get('content', '')
        image = request.FILES.get('image')
        video = request.FILES.get('video')

        # Validate that only one of image or video is provided
        if image and video:
            messages.error(request, _('لا يمكن إنشاء قصة تحتوي على صورة وفيديو في نفس الوقت.'))
            return render(request, 'posts/create_story.html')

        try:
            story = Story(
                author=request.user,
                content=content,
                image=image,
                video=video
            )
            story.full_clean()  # This will run model validation
            story.save()
            messages.success(request, _('تم إنشاء القصة بنجاح!'))
            return redirect('posts:stories_list')
        except ValidationError as e:
            if hasattr(e, 'message_dict'):
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            else:
                messages.error(request, _('خطأ في التحقق من القصة: ') + str(e))
        except Exception as e:
            logger.error(f"Error creating story: {str(e)}")
            messages.error(request, _('حدث خطأ أثناء إنشاء القصة.'))

    return render(request, 'posts/create_story.html')

@login_required
def view_story(request, story_id):
    """عرض قصة معينة"""
    story = get_object_or_404(Story.objects.select_related('author'), id=story_id)
    if not story.is_expired():
        story.views.add(request.user)
    return render(request, 'posts/view_story.html', {'story': story})

@login_required
@require_POST
def bookmark_toggle(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    bookmark = Bookmark.objects.filter(user=request.user, post=post)
    if bookmark.exists():
        bookmark.delete()
        messages.success(request, _('تم إزالة المنشور من المحفوظات.'))
    else:
        Bookmark.objects.create(user=request.user, post=post)
        messages.success(request, _('تم حفظ المنشور.'))
    return redirect(request.META.get('HTTP_REFERER', 'posts:post_list'))

@login_required
def saved_posts(request):
    bookmarks = Bookmark.objects.filter(user=request.user).select_related(
        'post__author'
    ).only(
        'post__id', 'post__content', 'post__created_at', 'post__author__username',
        'created_at'
    ).order_by('-created_at')
    posts = [b.post for b in bookmarks]
    return render(request, 'posts/saved_posts.html', {'posts': posts})


class PostListAPIView(generics.ListAPIView):
    serializer_class = PostSerializer

    def get_queryset(self):
        return visible_post_queryset(self.request.user).select_related('author').order_by('-created_at')
