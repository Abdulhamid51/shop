from django.contrib import admin
from django.utils.html import format_html
from django.db import models as djmodels

from .models import (
	Category, Brand, Shoe, Size, Tag,
	ProductImage, ShoeColor, ShoeColorImage, Stock,
	HeroSlide, ServiceItem, AboutBlock, Banner, BrandLogo, InstagramSetting,
	Testimonial
)


class CategoryAdmin(admin.ModelAdmin):
	list_display = ('name',)
	search_fields = ('name', 'description')


class BrandAdmin(admin.ModelAdmin):
	list_display = ('name',)
	search_fields = ('name', 'description')


class SizeAdmin(admin.ModelAdmin):
	list_display = ('value',)
	search_fields = ('value',)


class TagAdmin(admin.ModelAdmin):
	list_display = ('name',)
	search_fields = ('name',)


class StockAdmin(admin.ModelAdmin):
	list_display = ('color', 'size', 'quantity')
	search_fields = ('color__shoe__name', 'color__name', 'size__value')
	list_filter = ('size', 'color')


class ProductImageAdmin(admin.ModelAdmin):
	list_display = ('product', 'position', 'alt_text')
	search_fields = ('product__name', 'alt_text')


class ShoeColorImageAdmin(admin.ModelAdmin):
	list_display = ('product_color', 'position', 'alt_text')
	search_fields = ('product_color__name', 'alt_text')


class ProductImageInline(admin.TabularInline):
	model = ProductImage
	extra = 1
	fields = ('image', 'alt_text', 'position', 'preview')
	readonly_fields = ('preview',)

	def preview(self, obj):
		if obj.image:
			return format_html('<img src="{}" style="height:60px;" />', obj.image.url)
		return ''


class ShoeColorImageInline(admin.TabularInline):
	model = ShoeColorImage
	extra = 1
	fields = ('image', 'alt_text', 'position', 'preview')
	readonly_fields = ('preview',)

	def preview(self, obj):
		if obj.image:
			return format_html('<img src="{}" style="height:60px;" />', obj.image.url)
		return ''


class StockInline(admin.TabularInline):
	model = Stock
	extra = 1
	fields = ('size', 'quantity')


class ShoeColorAdmin(admin.ModelAdmin):
	list_display = ('shoe', 'name', 'css_class', 'get_price', 'is_active')
	inlines = [ShoeColorImageInline, StockInline]
	search_fields = ('name', 'shoe__name')


class ShoeAdmin(admin.ModelAdmin):
	list_display = ('name', 'brand', 'price', 'old_price', 'is_active', 'is_featured', 'is_new', 'times_ordered')
	list_filter = ('is_active', 'is_featured', 'is_new', 'brand', 'categories')
	search_fields = ('name', 'sku', 'description', 'short_description')
	inlines = [ProductImageInline]
	filter_horizontal = ('categories', 'tags')


admin.site.register(Category, CategoryAdmin)
admin.site.register(Brand, BrandAdmin)
admin.site.register(Size, SizeAdmin)
admin.site.register(Tag, TagAdmin)
admin.site.register(Shoe, ShoeAdmin)
admin.site.register(ShoeColor, ShoeColorAdmin)
admin.site.register(Stock, StockAdmin)
admin.site.register(ProductImage, ProductImageAdmin)
admin.site.register(ShoeColorImage, ShoeColorImageAdmin)


class HeroSlideAdmin(admin.ModelAdmin):
	list_display = ('title', 'order', 'is_active')
	list_editable = ('order', 'is_active')
	readonly_fields = ()


class ServiceItemAdmin(admin.ModelAdmin):
	list_display = ('title', 'subtitle', 'order', 'is_active')
	list_editable = ('order', 'is_active')


class AboutBlockAdmin(admin.ModelAdmin):
	list_display = ('title',)


class BannerAdmin(admin.ModelAdmin):
	list_display = ('title', 'order', 'is_active')
	list_editable = ('order', 'is_active')


class BrandLogoAdmin(admin.ModelAdmin):
	list_display = ('__str__', 'order', 'link', 'is_active')
	list_editable = ('order', 'is_active')


class InstagramSettingAdmin(admin.ModelAdmin):
	list_display = ('tag_text',)


class TestimonialAdmin(admin.ModelAdmin):
	list_display = ('name', 'who', 'text')


admin.site.register(HeroSlide, HeroSlideAdmin)
admin.site.register(ServiceItem, ServiceItemAdmin)
admin.site.register(AboutBlock, AboutBlockAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(BrandLogo, BrandLogoAdmin)
admin.site.register(InstagramSetting, InstagramSettingAdmin)
admin.site.register(Testimonial, TestimonialAdmin)

