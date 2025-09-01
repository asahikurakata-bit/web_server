from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib import messages
import docker
from .models import MinecraftServer
import re
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.conf import settings
import os
import logging
import zipfile
import shutil
import stripe
import json
import subprocess
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import miniupnpc as upnpc

client = docker.from_env()
stripe.api_key = settings.STRIPE_SECRET_KEY

def _stop_and_remove_container(container_id):
    if not container_id:
        return
    try:
        container = client.containers.get(container_id)
        container.stop()
        container.remove()
    except docker.errors.NotFound:
        pass
    except Exception as e:
        logging.error(f"Failed to stop and remove container {container_id}: {e}")

def _get_next_port():
    last = MinecraftServer.objects.order_by('-port').first()
    return last.port + 1 if last else 25565

def open_port(port, protocol='TCP'):
    try:
        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'add', 'rule',
            f'name=MCServer Port {port}', 'dir=in', 'action=allow',
            f'protocol={protocol}', f'localport={port}'
        ], check=True, capture_output=True, text=True, encoding='cp932', errors='ignore')
        logging.info(f"Opened port {port}/{protocol} in Windows Firewall.")
    except subprocess.CalledProcessError as e:
        if "ルールは既に存在します" not in e.stderr:
            logging.error(f"Failed to open port {port}: {e.stderr}")
    except Exception as e:
        logging.error(f"An unexpected error occurred in open_port: {e}")

def close_port(port, protocol='TCP'):
    try:
        subprocess.run([
            'netsh', 'advfirewall', 'firewall', 'delete', 'rule',
            f'name=MCServer Port {port}', f'protocol={protocol}', f'localport={port}'
        ], check=True, capture_output=True, text=True, encoding='cp932', errors='ignore')
        logging.info(f"Closed port {port}/{protocol} in Windows Firewall.")
    except subprocess.CalledProcessError as e:
        if "指定された条件に一致するルールはありません" not in e.stderr:
            logging.error(f"Failed to close port {port}: {e.stderr}")
    except Exception as e:
        logging.error(f"An unexpected error occurred in close_port: {e}")

def setup_port_forwarding(port, protocol='TCP'):
    try:
        u = upnpc.UPnP()
        u.discoverdelay = 200
        if u.discover() == 0:
            logging.warning("UPnP device (router) not found on the network.")
            return False
        u.selectigd()
        if u.getspecificportmapping(port, protocol) is not None:
             u.deleteportmapping(port, protocol)
        description = f'Server Port {port}'
        u.addportmapping(port, protocol, u.lanaddr, port, description, '')
        logging.info(f"UPnP: Successfully forwarded port {port}/{protocol}")
        return True
    except Exception as e:
        logging.error(f"UPnP failed to forward port {port}: {e}")
        return False

def remove_port_forwarding(port, protocol='TCP'):
    try:
        u = upnpc.UPnP()
        if u.discover() == 0:
            return
        u.selectigd()
        if u.getspecificportmapping(port, protocol) is not None:
            u.deleteportmapping(port, protocol)
            logging.info(f"UPnP: Successfully removed port forwarding for {port}/{protocol}")
    except Exception as e:
        logging.error(f"UPnP failed to remove port forwarding for {port}: {e}")

def home_page(request):
    return render(request, 'servermanager/home.html')

def about_page(request):
    return render(request, 'servermanager/about.html')

def terms_page(request):
    return render(request, 'servermanager/terms_page.html')

def inquiry_page(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        message_content = request.POST.get('message')
        try:
            send_mail(
                subject=f"お問い合わせ: {name} さんから",
                message=f"送信者: {name} <{email}>\n\n内容:\n{message_content}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=['asahikurakata@gmail.com'],
                fail_silently=False,
            )
            messages.success(request, 'お問い合わせありがとうございます。メールを送信しました。')
        except Exception as e:
            messages.error(request, f"メール送信に失敗しました: {e}")
        return redirect('inquiry_page')
    return render(request, 'servermanager/inquiry_page.html')

def news_page(request):
    news_list = [
        {'date': '2024-04-01', 'content': 'サーバーのメンテナンスを実施しました。'},
        {'date': '2024-03-15', 'content': '新プラン「プレミアム」を追加しました。'},
    ]
    return render(request, 'servermanager/news_page.html', {'news_list': news_list})

def signup_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        password_confirm = request.POST.get('password_confirm')
        email_regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
        if not email or not re.match(email_regex, email):
            messages.error(request, 'メールアドレスを正しく入力してください。')
            return redirect('signup_page')
        if password != password_confirm:
            messages.error(request, 'パスワードが一致しません。')
            return redirect('signup_page')
        if User.objects.filter(username=email).exists():
            messages.error(request, 'そのメールアドレスは既に使われています。')
            return redirect('signup_page')
        User.objects.create_user(username=email, email=email, password=password)
        messages.success(request, 'アカウントが作成されました。ログインしてください。')
        return redirect('login_page')
    return render(request, 'servermanager/signup_page.html')

def login_page(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next') or 'server_startup_page'
            return redirect(next_url)
        else:
            messages.error(request, 'メールアドレスまたはパスワードが正しくありません。')
    return render(request, 'servermanager/login_page.html')

def logout_view(request):
    auth_logout(request)
    return redirect('home_page')

def purchase_page(request):
    web_hosting_options = {
        'cpu': [
            {'name': '2 vCPU', 'price': 0},
            {'name': '4 vCPU', 'price': 500},
            {'name': '8 vCPU', 'price': 1500},
        ],
        'ram': [
            {'name': '2 GB', 'price': 0},
            {'name': '4 GB', 'price': 500},
            {'name': '8 GB', 'price': 1500},
        ],
        'storage': [
            {'name': '50 GB NVMe', 'price': 0},
            {'name': '100 GB NVMe', 'price': 500},
            {'name': '200 GB NVMe', 'price': 1000},
        ]
    }
    minecraft_options = {
        'ram': [
            {'name': '4 GB', 'price': 0},
            {'name': '8 GB', 'price': 1200},
            {'name': '16 GB', 'price': 3200},
        ],
        'cpu': [
            {'name': '高クロック 2 vCPU', 'price': 0},
            {'name': '高クロック 4 vCPU', 'price': 1000},
        ],
        'backup': [
            {'name': '自動バックアップ (毎日)', 'price': 0},
            {'name': '世代バックアップ (7日分)', 'price': 500},
        ]
    }
    context = {
        'web_base_price': 990,
        'web_options': web_hosting_options,
        'mc_base_price': 1280,
        'mc_options': minecraft_options,
    }
    return render(request, 'servermanager/payment_page.html', context)

@login_required
def checkout_page(request):
    if request.method != 'POST':
        return redirect('purchase_page')
    plan_type = request.POST.get('plan_type')
    total_price = request.POST.get('total_price')
    plan_description = request.POST.get('plan_description')
    if not plan_type or not total_price:
        messages.error(request, 'プラン情報が正しく送信されませんでした。')
        return redirect('purchase_page')
    specs = {}
    if plan_type == 'web':
        specs = {
            'cpu': request.POST.get('web_cpu', ''),
            'ram': request.POST.get('web_ram', ''),
            'storage': request.POST.get('web_storage', '')
        }
    elif plan_type == 'mc':
        specs = {
            'ram': request.POST.get('mc_ram', ''),
            'cpu': request.POST.get('mc_cpu', ''),
            'backup': request.POST.get('mc_backup', '')
        }
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(total_price),
            currency='jpy',
            description=plan_description,
            automatic_payment_methods={'enabled': True},
            metadata={
                'user_id': request.user.id,
                'plan_description': plan_description,
                'plan_type': plan_type,
                **specs
            }
        )
    except Exception as e:
        messages.error(request, f"決済の準備に失敗しました: {e}")
        return redirect('purchase_page')
    context = {
        'plan_description': plan_description,
        'total_price': total_price,
        'stripe_public_key': settings.STRIPE_PUBLIC_KEY,
        'client_secret': payment_intent.client_secret,
    }
    return render(request, 'servermanager/payment_checkout.html', context)

@require_POST
@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    endpoint_secret = settings.STRIPE_WEBHOOK_SECRET
    event = None
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError as e:
        logging.warning(f"Invalid webhook payload: {e}")
        return JsonResponse({'status': 'invalid payload'}, status=400)
    except stripe.error.SignatureVerificationError as e:
        logging.warning(f"Invalid webhook signature: {e}")
        return JsonResponse({'status': 'invalid signature'}, status=400)
    except Exception as e:
        logging.error(f"Webhook processing error: {e}")
        return JsonResponse({'status': 'error'}, status=500)
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        logging.info(f"PaymentIntent succeeded: {payment_intent.id}")
        metadata = payment_intent.get('metadata', {})
        user_id = metadata.get('user_id')
        plan_type = metadata.get('plan_type')
        plan_description = metadata.get('plan_description')
        if not user_id or not plan_type:
            logging.error(f"Webhook error: Missing metadata in PaymentIntent {payment_intent.id}")
            return JsonResponse({'status': 'error', 'message': 'Missing metadata'}, status=400)
        try:
            user = User.objects.get(id=user_id)
            cpu_cores_str = metadata.get('cpu', '2 vCPU')
            mem_limit_str = metadata.get('ram', '2 GB')
            storage_str = metadata.get('storage', '')
            backup_str = metadata.get('backup', '')
            cpu_cores = int(re.search(r'\d+', cpu_cores_str).group())
            mem_limit_gb = int(re.search(r'\d+', mem_limit_str).group())
            last_server = MinecraftServer.objects.order_by('-port').first()
            next_port = last_server.port + 1 if last_server else 25565
            MinecraftServer.objects.create(
                user=user,
                port=next_port,
                cpu_cores=cpu_cores,
                mem_limit=f"{mem_limit_gb}g",
                plan_type=plan_type,
                storage=storage_str,
                backup_type=backup_str,
                is_active=False,
                container_id=''
            )
            logging.info(f"Server created for user {user.id} with custom plan: {plan_description}")
        except User.DoesNotExist:
            logging.error(f"Webhook error: User with id '{user_id}' not found.")
        except Exception as e:
            logging.error(f"Server creation failed after payment: {e}")
            return JsonResponse({'status': 'error processing payment'}, status=500)
    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        logging.info(f"PaymentIntent failed: {payment_intent.id}")
    else:
        logging.info(f"Unhandled event type: {event['type']}")
    return JsonResponse({'status': 'success'})

@login_required
def server_startup_page(request):
    servers = MinecraftServer.objects.filter(user=request.user)
    return render(request, 'servermanager/server_startup_page.html', {'servers': servers})

@login_required
def delete_server(request, server_id):
    server = get_object_or_404(MinecraftServer, id=server_id, user=request.user)
    _stop_and_remove_container(server.container_id)
    protocol = 'UDP' if server.plan_type == 'be' else 'TCP'
    remove_port_forwarding(server.port, protocol)
    close_port(server.port, protocol)
    server.delete()
    messages.success(request, f"サーバー(ポート: {server.port})を削除しました。")
    return redirect('server_startup_page')

@login_required
def stop_server(request, server_id):
    server = get_object_or_404(MinecraftServer, id=server_id, user=request.user)
    _stop_and_remove_container(server.container_id)
    protocol = 'UDP' if server.plan_type == 'be' else 'TCP'
    remove_port_forwarding(server.port, protocol)
    close_port(server.port, protocol)
    server.is_active = False
    server.save()
    messages.success(request, f"サーバー (ポート: {server.port}) を停止しました。")
    return redirect('server_startup_page')

@login_required
def restart_server(request, server_id):
    server = get_object_or_404(MinecraftServer, id=server_id, user=request.user)
    _stop_and_remove_container(server.container_id)
    if server.plan_type == 'web':
        messages.warning(request, "ウェブサーバーの再起動は現在サポートされていません。")
        return redirect('server_startup_page')
    image = "itzg/minecraft-bedrock-server" if server.plan_type == 'be' else "itzg/minecraft-server"
    ports = {'19132/udp': server.port} if server.plan_type == 'be' else {'25565/tcp': server.port}
    protocol = 'UDP' if server.plan_type == 'be' else 'TCP'
    environment_vars = {'EULA': 'TRUE', 'MEMORY': server.mem_limit, 'VERSION': server.version}
    if server.plan_type == 'java':
        environment_vars.update({'TYPE': 'FORGE' if server.mods else 'VANILLA'})
        if server.mods:
            environment_vars['CF_MODS'] = server.mods
    if not setup_port_forwarding(server.port, protocol):
        messages.warning(request, f"ルーターの自動ポート開放(UPnP)に失敗しました。ポート {server.port} を手動で設定する必要がある場合があります。")
    volumes = {}
    if server.world_data_path and os.path.exists(server.world_data_path):
        volumes[server.world_data_path] = {'bind': '/data/world', 'mode': 'rw'}
        environment_vars['WORLD'] = '/data/world'
    try:
        container = client.containers.run(
            image=image, name=f"mcserver_{server.port}", ports=ports, detach=True,
            nano_cpus=int(server.cpu_cores * 1e9), mem_limit=server.mem_limit,
            environment=environment_vars, volumes=volumes
        )
        server.container_id = container.id
        open_port(server.port, protocol)
        server.is_active = True
        server.save()
        messages.success(request, f"サーバー (ポート: {server.port}) を起動しました。")
    except Exception as e:
        logging.error(f"Failed to start container for server {server.id}: {e}")
        messages.error(request, f"サーバーの起動に失敗しました: {e}")
        remove_port_forwarding(server.port, protocol)
        close_port(server.port, protocol)
    return redirect('server_startup_page')

@login_required
def manage_server(request, server_id):
    server = get_object_or_404(MinecraftServer, id=server_id, user=request.user)
    if server.plan_type == 'web':
        return render(request, 'servermanager/manage_web_server.html', {'server': server})
    available_versions = [
        'LATEST', '1.21', '1.20.4', '1.20.1', '1.19.4', '1.18.2', '1.16.5',
        '1.15.2', '1.14.4', '1.13.2', '1.12.2', '1.11.2', '1.10.2', '1.9.4',
        '1.8.9', '1.7.10', '1.6.4', '1.5.2', '1.4.7', '1.3.2', '1.2.5', '1.1'
    ]
    if request.method == 'POST':
        if 'update_settings' in request.POST:
            server.version = request.POST.get('version', 'LATEST')
            server.mods = request.POST.get('mods', '')
            server.save()
            messages.success(request, '設定を更新しました。サーバーを再起動すると適用されます。')
        elif 'upload_world' in request.POST:
            world_file = request.FILES.get('world_file')
            if not world_file or not world_file.name.endswith('.zip'):
                messages.error(request, 'ZIPファイルを選択してください。')
                return redirect('manage_server', server_id=server.id)
            worlds_base_dir = os.path.join(settings.BASE_DIR, 'worlds')
            server_world_dir = os.path.join(worlds_base_dir, str(server.id))
            if os.path.exists(server_world_dir):
                shutil.rmtree(server_world_dir)
            os.makedirs(server_world_dir)
            try:
                with zipfile.ZipFile(world_file, 'r') as zip_ref:
                    zip_ref.extractall(server_world_dir)
                world_root_path = None
                for root, _, files in os.walk(server_world_dir):
                    if 'level.dat' in files:
                        world_root_path = root
                        break
                if world_root_path:
                    server.world_data_path = world_root_path
                    server.save()
                    messages.success(request, 'ワールドをアップロードしました。再起動後に適用されます。')
                else:
                    shutil.rmtree(server_world_dir)
                    messages.error(request, 'ZIPファイルに有効なワールド(level.dat)が見つかりませんでした。')
            except zipfile.BadZipFile:
                messages.error(request, '無効なZIPファイルです。')
                shutil.rmtree(server_world_dir)
        return redirect('manage_server', server_id=server.id)
    return render(request, 'servermanager/manage_server.html', {'server': server, 'available_versions': available_versions})

@require_POST
@login_required
def admin_create_server(request):
    if not request.user.is_superuser:
        return JsonResponse({'error': '権限がありません。'}, status=403)
    try:
        data = json.loads(request.body)
        plan_type = data.get('plan_type')
        if not plan_type:
            return JsonResponse({'error': 'プランタイプが指定されていません。'}, status=400)
        cpu_cores_str = data.get('cpu', '2 vCPU')
        mem_limit_str = data.get('ram', '2 GB')
        storage_str = data.get('storage', '')
        backup_str = data.get('backup', '')
        cpu_cores = int(re.search(r'\d+', cpu_cores_str).group())
        mem_limit_gb = int(re.search(r'\d+', mem_limit_str).group())
        last_server = MinecraftServer.objects.order_by('-port').first()
        next_port = last_server.port + 1 if last_server else 25565
        MinecraftServer.objects.create(
            user=request.user,
            port=next_port,
            cpu_cores=cpu_cores,
            mem_limit=f"{mem_limit_gb}g",
            plan_type=plan_type,
            storage=storage_str,
            backup_type=backup_str,
            is_active=False,
            container_id=''
        )
        return JsonResponse({'success': True, 'redirect_url': reverse('server_startup_page')})
    except Exception as e:
        logging.error(f"Admin server creation error: {e}")
        return JsonResponse({'error': str(e)}, status=400)
