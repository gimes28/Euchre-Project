from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, "home.html")  # Reference the template in the root templates directory