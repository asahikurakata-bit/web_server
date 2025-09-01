# mcsite/urls.py

from django.contrib import admin
from django.urls import path, include
from servermanager import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # メインページ
    path('', views.home_page, name='home_page'),
    path('purchase/', views.purchase_page, name='purchase_page'), # プラン表示ページ
    
    # 決済フローのURL
    path('checkout/', views.checkout_page, name='checkout_page'), # 決済ページ
    path('api/stripe-webhook/', views.stripe_webhook, name='stripe_webhook'), # ★ Stripe Webhook用のURL
    path('api/admin-create-server/', views.admin_create_server, name='admin_create_server'),
    
    # ユーザー認証
    path('login/', views.login_page, name='login_page'),
    path('signup/', views.signup_page, name='signup_page'),
    path('logout/', views.logout_view, name='logout'),
    
    # サーバー管理
    path('server/startup/', views.server_startup_page, name='server_startup_page'),
    path('server/stop/<int:server_id>/', views.stop_server, name='stop_server'),
    path('server/delete/<int:server_id>/', views.delete_server, name='delete_server'),
    path('server/restart/<int:server_id>/', views.restart_server, name='restart_server'),
    path('server/manage/<int:server_id>/', views.manage_server, name='manage_server'),

    # その他
    path('inquiry/', views.inquiry_page, name='inquiry_page'),
    path('terms/', views.terms_page, name='terms_page'),
    path('news/', views.news_page, name='news_page'),
    path('about/', views.about_page, name='about_page'), # ★ 「私たちについて」ページのURLを追加
    path('accounts/', include('allauth.urls')),
]