import os

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import Post, Story


@receiver(post_delete, sender=Post)
def delete_post_files(sender, instance, **kwargs):
    """Delete image and video files when Post is deleted"""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
    if instance.video:
        if os.path.isfile(instance.video.path):
            os.remove(instance.video.path)

@receiver(post_delete, sender=Story)
def delete_story_files(sender, instance, **kwargs):
    """Delete image and video files when Story is deleted"""
    if instance.image:
        if os.path.isfile(instance.image.path):
            os.remove(instance.image.path)
    if instance.video:
        if os.path.isfile(instance.video.path):
            os.remove(instance.video.path)
