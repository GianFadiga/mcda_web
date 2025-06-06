# analyzer_app/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
import os
import json

class CustomUser(AbstractUser):
    email = models.EmailField(_('email address'), unique=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username obrigatório ainda

    def __str__(self):
        return self.email


class UserLog(models.Model):
    ACTION_CHOICES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete')
    ]
    
    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)
    old_data = models.TextField(null=True, blank=True)
    new_data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Log for user {self.email} at {self.timestamp}"
    
    def __str__(self):
        user_email = self.user.email if self.user else 'Unknown user'
        return f"Log for user {user_email} at {self.timestamp}"

class Analysis(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    creation_date = models.DateTimeField(auto_now_add=True)
    user = models.ForeignKey(CustomUser, related_name='analyses', on_delete=models.CASCADE)

    def delete(self, *args, **kwargs):
        # se tiver o campo file, tratar remoção do arquivo aqui
        # criar log de exclusão
        from .models import AnalysisLog
        AnalysisLog.objects.create(
            action='DELETE',
            analysis=self,
            old_data=json.dumps({
                'name': self.name,
                'description': self.description,
            })
        )
        super().delete(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Analyses"


class AnalysisLog(models.Model):
    ACTION_CHOICES = [
        ('INSERT', 'Insert'),
        ('UPDATE', 'Update'),
        ('DELETE', 'Delete')
    ]

    action = models.CharField(max_length=50, choices=ACTION_CHOICES)
    analysis = models.ForeignKey('Analysis', on_delete=models.CASCADE)  # << aqui a string
    timestamp = models.DateTimeField(auto_now_add=True)
    old_data = models.TextField(null=True, blank=True)
    new_data = models.TextField(null=True, blank=True)

    def __str__(self):
        return f"Log for analysis {self.analysis.name} at {self.timestamp}"