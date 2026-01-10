from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

class SiteSetting(models.Model):
	name = models.CharField('name', max_length=255)
	logo = models.ImageField(upload_to='logo')

	def __str__(self):
		return self.name

def validate_max_5_images(instance):
	"""Ensure no more than 5 images exist for a given color variant."""
	color = instance.product_color
	# When creating (no PK yet) include instance in count
	qs = ShoeColorImage.objects.filter(product_color=color)
	if instance.pk is None:
		count = qs.count() + 1
	else:
		count = qs.exclude(pk=instance.pk).count() + 1
	if count > 5:
		raise ValidationError(_('Each color may have at most 5 images (currently %(count)s).'), params={'count': count})


class Category(models.Model):
	name = models.CharField(max_length=120, unique=True)
	description = models.TextField(blank=True)

	class Meta:
		verbose_name = _('Category')
		verbose_name_plural = _('Categories')

	def __str__(self):
		return self.name


class Brand(models.Model):
	name = models.CharField(max_length=120, unique=True)
	description = models.TextField(blank=True)

	def __str__(self):
		return self.name


class Shoe(models.Model):
	"""Main product model representing a shoe product."""
	GENDER_SELECT = (
		(1, "Male"),
		(2, "Female"),
	)
	name = models.CharField(max_length=250)
	sku = models.CharField(max_length=60, blank=True, help_text=_('Optional product SKU'))
	gender = models.PositiveIntegerField(choices=GENDER_SELECT, blank=True, null=True)
	brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True)
	categories = models.ManyToManyField(Category, blank=True, related_name='products')
	tags = models.ManyToManyField('Tag', blank=True, related_name='products')
	short_description = models.CharField(max_length=500, blank=True)
	description = models.TextField(blank=True)
	price = models.DecimalField(max_digits=10, decimal_places=2)
	old_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
	is_active = models.BooleanField(default=True)
	is_featured = models.BooleanField(default=False)
	is_new = models.BooleanField(default=False)
	times_ordered = models.PositiveIntegerField(default=0)
	order = models.FloatField(default=200)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return self.name

	def get_available_colors(self):
		return self.colors.filter(is_active=True)

	def get_min_price(self):
		prices = [self.price]
		for c in self.colors.all():
			if c.price_modifier is not None:
				prices.append(self.price + c.price_modifier)
		return min(prices)

	@property
	def reviews_count(self):
		return self.reviews.count()

	@property
	def average_rating(self):
		rs = self.reviews.all()
		if not rs:
			return 0
		return sum(r.rating for r in rs) / rs.count()

	def main_image(self):
		img = self.images.order_by('position').first()
		return img.image.url if img else ''

	def get_image_binary(self):
		img = self.images.order_by('position').first()
		return img.image.open('rb') if img else ''

class Size(models.Model):
	"""Shoe size. You can store sizes as strings (EU/US/UK) or numbers."""
	value = models.CharField(max_length=20, help_text=_('e.g. 42, 9, M, L'))

	class Meta:
		unique_together = ('value',)

	def __str__(self):
		return self.value


class ShoeColor(models.Model):
	"""Color variant of a Shoe. Holds stock and optional price modifier."""
	shoe = models.ForeignKey(Shoe, related_name='colors', on_delete=models.CASCADE)
	name = models.CharField(max_length=80, help_text=_('Color name, e.g. Black'))
	hex_code = models.CharField(max_length=20, blank=True, help_text=_('#RRGGBB'))
	css_class = models.CharField(max_length=80, blank=True, help_text=_('Optional CSS class used in templates'))
	sku = models.CharField(max_length=80, blank=True, help_text=_('SKU for this variant'))
	price_modifier = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True, help_text=_('Amount to add/subtract from base price'))
	is_active = models.BooleanField(default=True)

	def __str__(self):
		return f"{self.shoe.name} — {self.name}"

	def get_price(self):
		if self.price_modifier is None:
			return self.shoe.price
		return self.shoe.price + self.price_modifier

	def available_sizes(self):
		return Size.objects.filter(stock__color=self, stock__quantity__gt=0)
	
	def main_image(self):
		img = self.images.all().order_by('position').first()
		return img.image.url if img else ''
	
	def get_image_binary(self):
		img = self.images.all().order_by('position').first()
		return img.image.open('rb') if img else ''


class Stock(models.Model):
	"""Stock per color and size."""
	color = models.ForeignKey(ShoeColor, related_name='stock', on_delete=models.CASCADE)
	size = models.ForeignKey(Size, related_name='stock', on_delete=models.CASCADE)
	quantity = models.PositiveIntegerField(default=0)

	# class Meta:
	# 	unique_together = ('color', 'size')

	def __str__(self):
		return f"{self.color} — {self.size}: {self.quantity}"


class ShoeColorImage(models.Model):
	"""Images tied to a specific color variant. Max 5 per color enforced in clean()."""
	product_color = models.ForeignKey(ShoeColor, related_name='images', on_delete=models.CASCADE)
	image = models.ImageField(upload_to='products/%Y/%m/%d/')
	alt_text = models.CharField(max_length=200, blank=True)
	position = models.PositiveSmallIntegerField(default=0, help_text=_('Ordering position'))

	class Meta:
		ordering = ['position']

	def save(self, *args, **kwargs):
		self.full_clean()
		super().save(*args, **kwargs)

	def __str__(self):
		return f"Image for {self.product_color} ({self.position})"


class ProductImage(models.Model):
	product = models.ForeignKey(Shoe, related_name='images', on_delete=models.CASCADE)
	image = models.ImageField(upload_to='products/%Y/%m/%d/')
	alt_text = models.CharField(max_length=200, blank=True)
	position = models.PositiveSmallIntegerField(default=0)

	class Meta:
		ordering = ['position']

	def __str__(self):
		return f"Image for {self.product} ({self.position})"


class Tag(models.Model):
	name = models.CharField(max_length=80, unique=True)
	def __str__(self):
		return self.name


class Review(models.Model):
	shoe = models.ForeignKey(Shoe, related_name='reviews', on_delete=models.CASCADE)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
	rating = models.PositiveSmallIntegerField(default=5)
	title = models.CharField(max_length=200, blank=True)
	body = models.TextField(blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.shoe.name} — {self.rating}"


class Cart(models.Model):
	added_date = models.DateTimeField(auto_now_add=True)
	product = models.ForeignKey(Shoe, on_delete=models.CASCADE)
	color = models.ForeignKey(ShoeColor, on_delete=models.CASCADE)
	size = models.ForeignKey(Size, on_delete=models.CASCADE)
	count = models.PositiveBigIntegerField(default=1)


class CartTree(models.Model):
	carts = models.ManyToManyField(Cart, blank=True, related_name='tree')


class Order(models.Model):
	created_date = models.DateTimeField(auto_now_add=True)
	fio = models.CharField(max_length=200)
	phone = models.CharField(max_length=20)
	phone2 = models.CharField(max_length=20, default='')
	address = models.TextField()
	carts = models.ManyToManyField(Cart)


# Homepage editable content models
class HeroSlide(models.Model):
	title = models.CharField(max_length=250, blank=True)
	subtitle = models.CharField(max_length=250, blank=True)
	description = models.TextField(blank=True)
	image = models.ImageField(upload_to='homepage/%Y/%m/%d/')
	button_text = models.CharField(max_length=80, blank=True)
	button_url = models.CharField(max_length=250, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order']

	def __str__(self):
		return self.title or f"Slide {self.pk}"


class ServiceItem(models.Model):
	icon_class = models.CharField(max_length=120, blank=True, help_text='CSS icon class (optional)')
	image = models.ImageField(upload_to='homepage/%Y/%m/%d/', blank=True, null=True)
	title = models.CharField(max_length=120)
	subtitle = models.CharField(max_length=250, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order']

	def __str__(self):
		return self.title


class AboutBlock(models.Model):
	title = models.CharField(max_length=250, blank=True)
	content = models.TextField(blank=True)
	signature = models.CharField(max_length=120, blank=True)
	logo = models.ImageField(upload_to='homepage/%Y/%m/%d/', blank=True, null=True)

	def __str__(self):
		return self.title or 'About block'


class Banner(models.Model):
	image = models.ImageField(upload_to='homepage/%Y/%m/%d/')
	title = models.CharField(max_length=250, blank=True)
	subtitle = models.CharField(max_length=250, blank=True)
	button_text = models.CharField(max_length=80, blank=True)
	button_url = models.CharField(max_length=250, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order']

	def __str__(self):
		return self.title or f'Banner {self.pk}'


class BrandLogo(models.Model):
	image = models.ImageField(upload_to='homepage/%Y/%m/%d/')
	link = models.CharField(max_length=250, blank=True)
	order = models.PositiveSmallIntegerField(default=0)
	is_active = models.BooleanField(default=True)

	class Meta:
		ordering = ['order']

	def __str__(self):
		return f'Brand {self.pk}'


class InstagramSetting(models.Model):
	tag_text = models.CharField(max_length=120, blank=True, default='#yourtag')

	def __str__(self):
		return self.tag_text
	
class Testimonial(models.Model):
	name  = models.CharField(max_length=220)
	text = models.TextField()
	who = models.CharField(max_length=120)
	image = models.ImageField(upload_to='products/%Y/%m/%d/', help_text='Kvadrat rasm bo`lsin')