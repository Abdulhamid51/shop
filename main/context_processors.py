from .models import SiteSetting

def site_settings(request):
    return {
        'site_setting': SiteSetting.objects.first()
    }