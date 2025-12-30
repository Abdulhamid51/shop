from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.db.models import Avg
from django.core.serializers.json import DjangoJSONEncoder
from django.http.response import JsonResponse
import json
import logging
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import redirect
from django.contrib import messages
from .models import *


def index(request):
	# Show 5 random active products on the homepage
	qs = Shoe.objects.filter(is_active=True).order_by('?')[:6]

	def serialize(product):
		return {
			'id': product.id,
			'name': product.name,
			'price': product.price,
			'old_price': product.old_price,
			'image': product.main_image(),
		}

	products = [serialize(p) for p in qs]

	# Load editable homepage content
	from .models import HeroSlide, ServiceItem, AboutBlock, Banner, BrandLogo, InstagramSetting

	hero_slides = list(HeroSlide.objects.filter(is_active=True).order_by('order'))
	services = list(ServiceItem.objects.filter(is_active=True).order_by('order'))
	about_block = AboutBlock.objects.first()
	banners = list(Banner.objects.filter(is_active=True).order_by('order'))
	brand_logos = list(BrandLogo.objects.filter(is_active=True).order_by('order'))
	inst_setting = InstagramSetting.objects.first()
	instagram_tag = inst_setting.tag_text if inst_setting else '#instagram'
	testimonials = Testimonial.objects.all().order_by('?')
	context = {
		'products': products,
		'hero_slides': hero_slides,
		'services': services,
		'about_block': about_block,
		'banners': banners,
		'brand_logos': brand_logos,
		'instagram_tag': instagram_tag,
		'testimonials': testimonials
	}

	return render(request, 'index.html', context)

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
	# page_no = request.GET.get('page', 1)
	# paginator = Paginator(qs, 20)
	# page_obj = paginator.get_page(page_no)
	page_obj = qs

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
			'colors': (lambda cols: [
				{'name': c.name, 'css_class': c.css_class, 'price': c.get_price()} 
				for c in (lambda it: [x for x in it])(cols) 
				if True
			])(product.colors.all() if True else []),
			'sizes': list(Size.objects.filter(stock__color__shoe=product).distinct()),
			'reviews_count': product.reviews_count,
			'average_rating': product.average_rating,
			'times_ordered': product.times_ordered,
		}

	products = [serialize(p) for p in page_obj]

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


def add_to_cart(request):
	if 'cart_tree' in request.session:
		cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
	else:
		cart_tree = CartTree.objects.create()
		request.session['cart_tree'] = cart_tree.id
	product_id = request.GET.get('product_id')
	color_id = request.GET.get('color_id')
	size_id = request.GET.get('size_id')
	count = request.GET.get('count', 1)
	cart_id = request.GET.get('cart_id')

	# If cart_id provided, update that cart entry directly (safer for cart page updates)
	if cart_id:
		try:
			cart_obj = Cart.objects.get(id=cart_id)
			cart_obj.count = int(count)
			cart_obj.save()
			return JsonResponse({'success': True, 'cart': cart_obj.id, 'tree': request.session.get('cart_tree')})
		except Cart.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'cart not found'})
	# Find existing cart item within the current CartTree
	existing_cart = Cart.objects.filter(
		product_id=product_id,
		color_id=color_id,
		size_id=size_id,
		id__in=cart_tree.carts.values_list('id', flat=True)
	).first()
	if existing_cart:
		cart = existing_cart
		cart.count = int(count)
		cart.save()
		created = False
	else:
		# Create a new Cart item and attach to the tree
		cart = Cart.objects.create(
			product_id=product_id,
			color_id=color_id,
			size_id=size_id,
			count=int(count)
		)
		cart_tree.carts.add(cart)
		cart_tree.save()
		created = True
	
	return JsonResponse({
		'success': True,
		'cart': cart.id,
		'tree': request.session['cart_tree']
	})

def change_cart_view(request):
	if 'cart_tree' in request.session:
		cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
	else:
		cart_tree = CartTree.objects.create()
		request.session['cart_tree'] = cart_tree.id
	product_id = request.GET.get('product_id')
	color_id = request.GET.get('color_id')
	size_id = request.GET.get('size_id')
	cart_qs = Cart.objects.filter(
		product_id=product_id,
		color_id=color_id,
		size_id=size_id,
		id__in=cart_tree.carts.values_list('id', flat=True)
	)
	if cart_qs.exists():
		last_cart = cart_qs.last()
		return JsonResponse({
			'view': 'remove',
			'count': last_cart.count
		})
	else:
		return JsonResponse({
			'view': 'add',
			'count': 1
		})


def remove_from_cart(request):
	"""Remove a cart item from the current CartTree if it exists."""
	if 'cart_tree' in request.session:
		cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
	else:
		cart_tree = CartTree.objects.create()
		request.session['cart_tree'] = cart_tree.id
	product_id = request.GET.get('product_id')
	color_id = request.GET.get('color_id')
	size_id = request.GET.get('size_id')
	cart_id = request.GET.get('cart_id')

	# If cart_id supplied remove by id
	if cart_id:
		try:
			cart_obj = Cart.objects.get(id=cart_id)
			if cart_tree:
				cart_tree.carts.remove(cart_obj)
			try:
				cart_obj.delete()
			except Exception:
				pass
			return JsonResponse({'success': True, 'view': 'add', 'count': 1})
		except Cart.DoesNotExist:
			return JsonResponse({'success': False, 'message': 'not found', 'view': 'add', 'count': 1})
	cart_qs = Cart.objects.filter(
		product_id=product_id,
		color_id=color_id,
		size_id=size_id,
		id__in=cart_tree.carts.values_list('id', flat=True)
	)
	if cart_qs.exists():
		cart = cart_qs.last()
		# remove association and delete cart entry
		cart_tree.carts.remove(cart)
		try:
			cart.delete()
		except Exception:
			pass
		return JsonResponse({'success': True, 'view': 'add', 'count': 1})
	else:
		return JsonResponse({'success': False, 'message': 'not found', 'view': 'add', 'count': 1})


def cart_view(request):
	"""Render the user's current cart page based on session CartTree."""
	if 'cart_tree' in request.session:
		try:
			cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
		except CartTree.DoesNotExist:
			cart_tree = None
	else:
		cart_tree = None

	cart_items = []
	subtotal = 0
	if cart_tree:
		qs = cart_tree.carts.select_related('product', 'color', 'size').all()
		for c in qs:
			unit_price = c.color.get_price() if c.color else c.product.price
			total = unit_price * c.count
			subtotal += total
			cart_items.append({
				'id': c.id,
				'product_id': c.product.id,
				'product_name': c.product.name,
				'product_image': c.product.main_image(),
				'color_name': c.color.name if c.color else '',
				'size_value': c.size.value if c.size else '',
				'unit_price': float(unit_price),
				'count': c.count,
				'total': float(total),
			})

	context = {
		'cart_items': cart_items,
		'subtotal': subtotal,
	}
	return render(request, 'cart.html', context)


def checkout(request):
	"""Handle checkout form: create Order and move current CartTree carts into the Order."""
	if request.method == 'POST':
		fio = request.POST.get('fio', '').strip()
		phone = request.POST.get('phone', '').strip()
		phone2 = request.POST.get('phone2', '').strip()
		address = request.POST.get('address', '').strip()

		# Basic validation
		if not fio or not phone or not address:
			# Re-render cart with an error message
			if 'cart_tree' in request.session:
				try:
					cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
				except CartTree.DoesNotExist:
					cart_tree = None
			else:
				cart_tree = None

			cart_items = []
			subtotal = 0
			if cart_tree:
				qs = cart_tree.carts.select_related('product', 'color', 'size').all()
				for c in qs:
					unit_price = c.color.get_price() if c.color else c.product.price
					total = unit_price * c.count
					subtotal += total
					cart_items.append({
						'id': c.id,
						'product_id': c.product.id,
						'product_name': c.product.name,
						'color_name': c.color.name if c.color else '',
						'size_value': c.size.value if c.size else '',
						'unit_price': float(unit_price),
						'count': c.count,
						'total': float(total),
					})

			return render(request, 'cart.html', {
				'cart_items': cart_items,
				'subtotal': subtotal,
				'checkout_error': 'Заполните все обязательные поля.'
			})

		# Create order
		order = Order.objects.create(fio=fio, phone=phone, phone2=phone2, address=address)

		# Move carts into order
		if 'cart_tree' in request.session:
			try:
				cart_tree = CartTree.objects.get(id=request.session.get('cart_tree'))
			except CartTree.DoesNotExist:
				cart_tree = None
		else:
			cart_tree = None

		moved_items = []
		if cart_tree:
			qs = list(cart_tree.carts.select_related('product', 'color', 'size').all())
			if qs:
				order.carts.set(qs)
				# Detach carts from cart_tree
				cart_tree.carts.clear()
				order_total = 0
				for c in qs:
					unit_price = c.color.get_price() if c.color else c.product.price
					total = unit_price * c.count
					order_total += total
					moved_items.append({
						'product_name': c.product.name,
						'color_name': c.color.name if c.color else '',
						'size_value': c.size.value if c.size else '',
						'count': c.count,
						'unit_price': float(unit_price),
						'total': float(total),
					})
			else:
				order_total = 0

		# Try to send order invoice to Telegram
		try:
			send_order_to_telegram(order)
		except Exception:
			logger = logging.getLogger(__name__)
			logger.exception('Failed to send order to Telegram')

		return render(request, 'checkout_success.html', {'order': order, 'items': moved_items, 'order_total': order_total})

	# GET -> redirect to cart
	return render(request, 'cart.html', {})

def send_order_to_telegram(order):
    import logging, requests
    from django.conf import settings

    logger = logging.getLogger(__name__)
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
    if not token or not chat_id:
        return False

    items_text = []
    subtotal = 0

    for i, c in enumerate(order.carts.select_related('product', 'color', 'size'), start=1):
        unit_price = c.color.get_price() if c.color else c.product.price
        total = unit_price * c.count
        subtotal += total

        options = []
        if c.color:
            options.append(f"🎨 {c.color.name}")
        if c.size:
            options.append(f"📏 {c.size.value}")

        items_text.append(
            f"<b>{i}. {c.product.name}</b>\n"
            f"   {' | '.join(options)}\n"
            f"   💵 {unit_price:.2f} ₽ × {c.count} = <b>{total:.2f} ₽</b>"
        )

    phone2_text = f"📞 <b>Доп. телефон:</b> {order.phone2}\n" if order.phone2 else ""

    message = (
		f"🛒 <b>НОВЫЙ ЗАКАЗ #{order.id}</b>\n"
		f"━━━━━━━━━━━━━━━\n"
		f"👤 <b>Клиент:</b> {order.fio}\n"
		f"📞 <b>Телефон:</b> {order.phone}\n"
		f"{phone2_text}"
		f"📍 <b>Адрес доставки:</b>\n{order.address}\n"
		f"\n📦 <b>Товары:</b>\n"
		f"{chr(10).join(items_text)}\n"
		f"\n━━━━━━━━━━━━━━━\n"
		f"💰 <b>Итого:</b> <b>{subtotal:.2f} ₽</b>"
	)

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }

    resp = requests.post(url, data=payload, timeout=10)
    return resp.status_code == 200


def send_contact_to_telegram(name: str, phone: str, message: str) -> bool:
	"""Send contact form message to Telegram chat configured in settings.

	Uses `settings.TELEGRAM_BOT_TOKEN` and `settings.TELEGRAM_CHAT_ID`.
	Returns True on success, False otherwise.
	"""
	logger = logging.getLogger(__name__)
	token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
	chat_id = getattr(settings, 'TELEGRAM_CHAT_ID', None)
	if not token or not chat_id:
		logger.warning('Telegram token or chat_id not configured; skipping contact send')
		return False

	text_lines = [f"<b>Новое сообщение с контактной формы</b>"]
	text_lines.append(f"Имя: {name}")
	text_lines.append(f"Телефон: {phone}")
	text_lines.append("\nСообщение:")
	# Escape limited HTML (we use parse_mode=HTML) - keep simple
	body = message
	text_lines.append(body)

	payload = {
		'chat_id': chat_id,
		'text': "\n".join(text_lines),
		'parse_mode': 'HTML'
	}

	url = f"https://api.telegram.org/bot{token}/sendMessage"
	resp = requests.post(url, data=payload, timeout=10)
	if resp.status_code != 200:
		logger.error('Telegram API responded with %s: %s', resp.status_code, resp.text)
		return False
	return True


def contact(request):
	"""Render contact form and send email on POST.

	Expects `settings.CONTACT_EMAIL` (receiver) and proper email backend configured.
	"""
	if request.method == 'POST':
		name = request.POST.get('name', '').strip()
		phone = request.POST.get('phone', '').strip()
		message = request.POST.get('message', '').strip()

		if not name or not phone or not message:
			messages.error(request, 'Пожалуйста, заполните все поля.')
			return render(request, 'contact.html', {'name': name, 'phone': phone, 'message': message})

		full_message = f"От: {name} <{phone}>\n\n{message}"

		try:
			try:
				send_contact_to_telegram(name=name, phone=phone, message=message)
			except Exception:
				logging.getLogger(__name__).exception('Failed to send contact message to Telegram')

			messages.success(request, 'Спасибо! Ваше сообщение отправлено.')
			return redirect('main:contact')
		except Exception:
			logging.getLogger(__name__).exception('Failed to send contact phone')
			messages.error(request, 'Произошла ошибка при отправке. Попробуйте позже.')
			return render(request, 'contact.html', {'name': name, 'phone': phone, 'message': message})

	return render(request, 'contact.html', {})


# for i in Stock.objects.all():
# 	i.quantity = 100
# 	i.save()
# 	print(i.id)