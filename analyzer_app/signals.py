# analyzer_app/signals.py
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.signals import user_logged_in, user_logged_out
from .models import CustomUser, Analysis, UserLog, AnalysisLog
import json

@receiver(post_save, sender=CustomUser)
def log_user_changes(sender, instance, created, **kwargs):
    if created:
        action = 'INSERT'
        old_data = None
    else:
        action = 'UPDATE'
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_data = json.dumps({
                'username': old_instance.username,
                'email': old_instance.email,
                'first_name': old_instance.first_name,
                'last_name': old_instance.last_name,
            })
        except sender.DoesNotExist:
            old_data = None

    new_data = json.dumps({
        'username': instance.username,
        'email': instance.email,
        'first_name': instance.first_name,
        'last_name': instance.last_name,
    })

    UserLog.objects.create(
        action=action,
        user=instance,
        old_data=old_data,
        new_data=new_data
    )

@receiver(post_delete, sender=CustomUser)
def log_user_deletion(sender, instance, **kwargs):
    old_data = json.dumps({
        'username': instance.username,
        'email': instance.email,
        'first_name': instance.first_name,
        'last_name': instance.last_name,
    })
    UserLog.objects.create(
        action='DELETE',
        user=instance,
        old_data=old_data
    )

@receiver(post_save, sender=Analysis)
def log_analysis_changes(sender, instance, created, **kwargs):
    if created:
        action = 'INSERT'
        old_data = None
    else:
        action = 'UPDATE'
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            old_data = json.dumps({
                'name': old_instance.name,
                'description': old_instance.description,
            })
        except sender.DoesNotExist:
            old_data = None

    new_data = json.dumps({
        'name': instance.name,
        'description': instance.description,
    })

    AnalysisLog.objects.create(
        action=action,
        analysis=instance,
        old_data=old_data,
        new_data=new_data
    )

@receiver(post_delete, sender=Analysis)
def log_analysis_deletion(sender, instance, **kwargs):
    old_data = json.dumps({
        'name': instance.name,
        'description': instance.description,
    })
    AnalysisLog.objects.create(
        action='DELETE',
        analysis=instance,
        old_data=old_data
    )

@receiver(user_logged_in)
def log_user_login(sender, request, user, **kwargs):
    UserLog.objects.create(
        action='LOGIN',
        user=user,
        old_data=None,
        new_data=json.dumps({'event': 'login'}),
    )

@receiver(user_logged_out)
def log_user_logout(sender, request, user, **kwargs):
    UserLog.objects.create(
        action='LOGOUT',
        user=user,
        old_data=None,
        new_data=json.dumps({'event': 'logout'}),
    )
