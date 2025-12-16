from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from django.core.serializers.json import DjangoJSONEncoder
import json
from .models import *


def shop(request):
	qs = Shoe.objects.filter(is_active=True).prefetch_related('images', 'colors', 'categories', 'tags')

	# Filters
	category = request.GET.get('category')
	if category:
		qs = qs.filter(categories=category)

	tag = request.GET.get('tag')
	if tag:
		qs = qs.filter(tags=tag)

	size = request.GET.get('size')
	if size:
		qs = qs.filter(colors__stock__size__value=size, colors__stock__quantity__gt=0)

	color = request.GET.get('color')
	if color:
		qs = qs.filter(colors__name__iexact=color)

	q = request.GET.get('q')
	if q:
		qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q) | Q(short_description__icontains=q))

	# Sorting
	sort = request.GET.get('sort')
	if sort == 'name':
		qs = qs.order_by('name')
	elif sort == 'price':
		qs = sorted(qs, key=lambda p: p.get_min_price())
	else:
		qs = qs.order_by('-created_at')

	# Pagination
	page_no = request.GET.get('page', 1)
	paginator = Paginator(qs, 20)
	page_obj = paginator.get_page(page_no)

	def serialize(product):
		return {
			'id': product.id,
			'name': product.name,
			'price': product.price,
			'old_price': product.old_price,
			'short_description': product.short_description,
			'categories': list(product.categories.all()),
			'tags': list(product.tags.all()),
			'image': product.main_image(),
			'images': [img.image.url for img in product.images.all()],
			'colors': [{'name': c.name, 'css_class': c.css_class, 'price': c.get_price()} for c in product.colors.all()],
			'sizes': list(Size.objects.filter(stock__color__shoe=product).distinct()),
			'reviews_count': product.reviews_count,
			'average_rating': product.average_rating,
			'times_ordered': product.times_ordered,
		}

	products = [serialize(p) for p in page_obj.object_list]

	context = {
		'products': products,
		'page_obj': page_obj,
		'categories': Category.objects.all(),
		'sizes': Size.objects.all(),
		'colors': ShoeColor.objects.values('name').distinct(),
		'tags': Tag.objects.all() if 'Tag' in globals() else [],
	}
	print(context)
	return render(request, 'shop.html', context)


def product_detail(request, id):
    product = get_object_or_404(
        Shoe.objects.select_related('brand')
                    .prefetch_related('images', 'colors__images', 'colors__stock__size', 
                                     'categories', 'tags', 'reviews__user'),
        id=id,
        is_active=True
    )
    
    # Get available colors with their images and sizes
    colors_data = []
    for color in product.colors.filter(is_active=True):
        # Get sizes available for this color
        available_sizes = Size.objects.filter(
            stock__color=color, 
            stock__quantity__gt=0
        ).distinct()
        
        # Get images for this color
        color_images = [img.image.url for img in color.images.order_by('position')]
        
        # Create sizes list
        sizes_list = [{'id': size.id, 'value': size.value} for size in available_sizes]
        
        color_data = {
            'id': color.id,
            'name': color.name,
            'hex_code': color.hex_code,
            'css_class': color.css_class,
            'price': float(color.get_price()),
            'sku': color.sku,
            'images': color_images,
            'sizes': sizes_list,
        }
        colors_data.append(color_data)
    
    # Get all unique sizes for the product
    all_sizes = Size.objects.filter(
        stock__color__shoe=product, 
        stock__quantity__gt=0
    ).distinct()
    
    # Get reviews
    reviews = Review.objects.filter(shoe=product).select_related('user').order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    
    # Get related products
    related_products = Shoe.objects.filter(
        categories__in=product.categories.all(),
        is_active=True
    ).exclude(id=product.id).distinct()[:4]
    
    def serialize_product(product):
        return {
            'id': product.id,
            'name': product.name,
            'price': product.price,
            'old_price': product.old_price,
            'image': product.main_image(),
            'reviews_count': product.reviews.count(),
            'average_rating': product.average_rating,
        }
    
    serialized_related = [serialize_product(p) for p in related_products]
    
    # Convert colors data to JSON for JavaScript
    colors_json = json.dumps(colors_data, cls=DjangoJSONEncoder)
    
    context = {
        'product': product,
        'colors': colors_data,
        'colors_json': colors_json,  # JSON formatdagi colors
        'sizes': all_sizes,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'related_products': serialized_related,
        'discount_percentage': 0,
    }
    
    if product.old_price and product.old_price > product.price:
        context['discount_percentage'] = round(((product.old_price - product.price) / product.old_price) * 100)
    
    return render(request, 'product-details.html', context)