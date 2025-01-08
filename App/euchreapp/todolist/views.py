from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods

from .models import Todo

# Create your views here.
def index(request):
    todos = Todo.objects.all()
    return render(request, "todos.html", {"todo_list": todos})


# Require this be a post type method by using the decorator
@require_http_methods(["POST"])
def add(request):
    title = request.POST["title"]
    todo = Todo(title=title)
    todo.save()
    return redirect("index")

# Update function will query for id, then update objects and change complete flag, then save before redirect (reloading page after save to update)
def update(request, todo_id):
    todo = Todo.objects.get(id=todo_id)
    todo.complete = not todo.complete
    todo.save()
    return redirect("index")

# Delete function will query for id, then delete object and change complete flag, then save before redirect (reloading page after delete to update)
def delete(request, todo_id):
    todo = Todo.objects.get(id=todo_id)
    todo.complete = not todo.complete
    todo.delete()
    return redirect("index")