from django.urls import path
from . import views

# Here we add the URL paths and functions which will update the page 
urlpatterns = [
    path('', views.index, name="index"),
    path('add', views.add, name="add"),
    path('delete/<int:todo_id>/', views.delete, name="delete"),
    path('update/<int:todo_id>/', views.update, name="update"),
]