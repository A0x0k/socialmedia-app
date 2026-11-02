from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django_ratelimit.decorators import ratelimit

from posts.models import Post
from posts.utils import visible_post_queryset


@ratelimit(key='user', rate='30/m', method='GET', block=True)
@login_required
def search(request):
    """البحث في المنشورات والمستخدمين"""
    query = request.GET.get('q', '')
    search_type = request.GET.get('type', 'all')

    blocked = request.user.profile.blocked_users.values_list('user_id', flat=True)
    blocked_by = request.user.profile.blocked_by.values_list('user_id', flat=True)
    excluded = set(blocked) | set(blocked_by)

    if query:
        if search_type == 'posts' or search_type == 'all':
            posts = visible_post_queryset(request.user).filter(
                Q(content__icontains=query) |
                Q(author__username__icontains=query)
            ).select_related('author').distinct().order_by('-created_at')
        else:
            posts = Post.objects.none()

        if search_type == 'users' or search_type == 'all':
            users = User.objects.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            ).exclude(id__in=excluded).select_related('profile').order_by('username')
        else:
            users = User.objects.none()
    else:
        posts = Post.objects.none()
        users = User.objects.none()

    # ترقيم الصفحات للمنشورات
    posts_paginator = Paginator(posts, 10)
    posts_page = request.GET.get('posts_page')
    posts_results = posts_paginator.get_page(posts_page)

    # ترقيم الصفحات للمستخدمين
    users_paginator = Paginator(users, 20)
    users_page = request.GET.get('users_page')
    users_results = users_paginator.get_page(users_page)

    context = {
        'query': query,
        'search_type': search_type,
        'posts': posts_results,
        'users': users_results,
    }

    return render(request, 'searchapp/search_results.html', context)

@ratelimit(key='user', rate='30/m', method='GET', block=True)
@login_required
def advanced_search(request):
    """البحث المتقدم"""
    query = request.GET.get('q', '')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    author = request.GET.get('author')
    has_image = request.GET.get('has_image')

    posts = visible_post_queryset(request.user).select_related('author')

    if query:
        posts = posts.filter(content__icontains=query)

    if date_from:
        posts = posts.filter(created_at__gte=date_from)

    if date_to:
        posts = posts.filter(created_at__lte=date_to)

    if author:
        posts = posts.filter(author__username__icontains=author)

    if has_image:
        posts = posts.exclude(image__isnull=True).exclude(image__exact='')

    posts = posts.order_by('-created_at')

    # ترقيم الصفحات
    paginator = Paginator(posts, 10)
    page = request.GET.get('page')
    results = paginator.get_page(page)

    context = {
        'query': query,
        'date_from': date_from,
        'date_to': date_to,
        'author': author,
        'has_image': has_image,
        'posts': results,
    }

    return render(request, 'searchapp/advanced_search.html', context)
