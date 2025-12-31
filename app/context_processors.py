from .models import Category

def category_context(request):
    categories = Category.objects.all().order_by('-created_at')
    return {'categories': categories}
