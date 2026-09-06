from django.urls import path, include
from . import views

urlpatterns = [
    path('add/', views.note_view, name='add_note'),
]
