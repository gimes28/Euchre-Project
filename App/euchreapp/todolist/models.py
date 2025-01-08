from django.db import models

# Create your models here.
# These will automatically create a database model to use the built in sqlite3
class Todo(models.Model):
    title=models.CharField(max_length=350)
    complete=models.BooleanField(default=False)
    
    def __str__(self):
        return self.title