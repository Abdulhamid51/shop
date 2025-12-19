from django.contrib import admin
from django.utils.html import format_html

from .models import (
	Category, Brand, Shoe, Size, Tag,
	ProductImage, ShoeColor, ShoeColorImage, Stock,
    HeroSlide, ServiceItem, AboutBlock, Banner, BrandLogo, InstagramSetting,
)


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


admin.site.register(Category)
admin.site.register(Brand)
admin.site.register(Size)
admin.site.register(Tag)
admin.site.register(Shoe, ShoeAdmin)
admin.site.register(ShoeColor, ShoeColorAdmin)


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


admin.site.register(HeroSlide, HeroSlideAdmin)
admin.site.register(ServiceItem, ServiceItemAdmin)
admin.site.register(AboutBlock, AboutBlockAdmin)
admin.site.register(Banner, BannerAdmin)
admin.site.register(BrandLogo, BrandLogoAdmin)
admin.site.register(InstagramSetting, InstagramSettingAdmin)

