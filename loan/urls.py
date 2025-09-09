from django.contrib import admin
from django.urls import path
from myloan import views  # This imports all views from myloan/views.py
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.welcome, name='welcome'),
    path('signin/', views.signin, name='signin'),
    path('signup/', views.signup, name='signup'),
    path('home/', views.home, name='home'),
    path('apply/', views.apply, name='apply'),
    path('loan-success/', views.loan_success, name='loan_success'),
    path('record-payment/<int:loan_id>/', views.record_payment, name='record_payment'),
    path('extract_id_data/', views.extract_id_data, name='extract_id_data'),
    path('history/', views.loan_history, name='loan_history'),
    path('settings/', views.settings_view, name='settings'),
    path('payment/', views.payment, name='payment'),
    path('apply/loan_success', views.loan_success,name='loan_success'),
    path('payment/success/', views.payment_success, name='payment_success'),
    path('payment/cancel/', views.payment_cancel, name='payment_cancel'),
    
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)