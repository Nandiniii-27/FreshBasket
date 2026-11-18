
from django.shortcuts import render, redirect, get_object_or_404
from .models import Product
from django.db.models import Q
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import logout as auth_logout
from django.contrib.auth.decorators import login_required
from .models import DeliveryAddress
from .forms import DeliveryAddressForm
from decimal import Decimal
from django.db import transaction
from django.contrib.auth.decorators import login_required
from .models import Order, OrderItem, DeliveryAddress
def home(request):
    query = request.GET.get('q', '')

    products = Product.objects.all()

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(category__icontains=query)
        )

    return render(request, 'store/home.html', {
        'products': products,
        'query': query
    })

def add_to_cart(request, product_id):

    product = get_object_or_404(Product, id=product_id)

    cart = request.session.get('cart', {})

    product_id = str(product.id)

    if product.stock > 0:
        current_quantity = cart.get(product_id, 0)

        if current_quantity < product.stock:
            cart[product_id] = current_quantity + 1

    request.session['cart'] = cart
    messages.success(request, "Product added to cart successfully!")
    return redirect('cart')
def cart(request):
    cart = request.session.get('cart', {})

    cart_items = []
    total = 0

    for product_id, quantity in cart.items():
        product = get_object_or_404(Product, id=product_id)

        subtotal = product.price * quantity
        total += subtotal

        cart_items.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })

    return render(request, 'store/cart.html', {
        'cart_items': cart_items,
        'total': total
    })
def update_cart(request, product_id):

    if request.method == 'POST':

        cart = request.session.get('cart', {})
        product_id = str(product_id)

        action = request.POST.get('action')

        if product_id in cart:

            if action == 'increase':

                product = get_object_or_404(Product, id=product_id)

                if cart[product_id] < product.stock:
                    cart[product_id] += 1

            elif action == 'decrease':

                cart[product_id] -= 1

                if cart[product_id] <= 0:
                    del cart[product_id]

        request.session['cart'] = cart

    return redirect('cart')


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful!')
            return redirect('home')

    else:
        form = UserCreationForm()

    return render(request, 'store/register.html', {'form': form})

# User Login
def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)

        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('home')

    else:
        form = AuthenticationForm()

    return render(request, 'store/login.html', {'form': form})


# User Logout
def user_logout(request):
    if request.method == 'POST':
        auth_logout(request)
        messages.success(request, 'You have logged out successfully!')

    return redirect('home')

@login_required
def delivery_address(request):

    if request.method == 'POST':
        form = DeliveryAddressForm(request.POST)

        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            address.save()

            messages.success(
                request,
                'Delivery address saved successfully!'
            )

            return redirect('cart')

    else:
        form = DeliveryAddressForm()

    addresses = DeliveryAddress.objects.filter(user=request.user)

    return render(request, 'store/address.html', {
        'form': form,
        'addresses': addresses
    })

# CHECKOUT PAGE
@login_required
def checkout(request):

    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')

    cart_items = []
    total = Decimal('0.00')

    for product_id, quantity in cart.items():

        try:
            product = Product.objects.get(id=product_id)
            quantity = int(quantity)

            if quantity <= 0:
                continue

            subtotal = product.price * quantity

            cart_items.append({
                'product': product,
                'quantity': quantity,
                'subtotal': subtotal
            })

            total += subtotal

        except Product.DoesNotExist:
            continue

    if not cart_items:
        messages.error(request, 'Your cart has no valid products.')
        return redirect('cart')

    addresses = DeliveryAddress.objects.filter(user=request.user)

    if not addresses.exists():
        messages.error(request, 'Please add a delivery address first.')
        return redirect('address')

    return render(request, 'store/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'addresses': addresses
    })


# PLACE ORDER
@login_required
@transaction.atomic
def place_order(request):

    if request.method != 'POST':
        return redirect('checkout')

    cart = request.session.get('cart', {})

    if not cart:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')

    address_id = request.POST.get('address')

    address = get_object_or_404(
        DeliveryAddress,
        id=address_id,
        user=request.user
    )

    order_products = []
    total = Decimal('0.00')

    for product_id, quantity in cart.items():

        product = get_object_or_404(
            Product.objects.select_for_update(),
            id=product_id
        )

        quantity = int(quantity)

        if quantity <= 0:
            messages.error(request, 'Invalid product quantity.')
            return redirect('cart')

        if product.stock < quantity:
            messages.error(
                request,
                f'Not enough stock for {product.name}.'
            )
            return redirect('cart')

        subtotal = product.price * quantity
        total += subtotal

        order_products.append({
            'product': product,
            'quantity': quantity,
            'subtotal': subtotal
        })

    order = Order.objects.create(
        user=request.user,
        address=address,
        total_amount=total
    )

    for item in order_products:

        product = item['product']
        quantity = item['quantity']

        OrderItem.objects.create(
            order=order,
            product=product,
            product_name=product.name,
            price=product.price,
            quantity=quantity
        )

        product.stock -= quantity
        product.save(update_fields=['stock'])

    request.session['cart'] = {}
    request.session.modified = True

    messages.success(request, 'Your order has been placed successfully!')

    return redirect('order_success', order_id=order.id)


# ORDER SUCCESS
@login_required
def order_success(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(request, 'store/order_success.html', {
        'order': order
    })


# ORDER HISTORY
@login_required
def order_history(request):

    orders = Order.objects.filter(
        user=request.user
    ).order_by('-created_at')

    return render(request, 'store/order_history.html', {
        'orders': orders
    })


# ORDER DETAILS
@login_required
def order_detail(request, order_id):

    order = get_object_or_404(
        Order,
        id=order_id,
        user=request.user
    )

    return render(request, 'store/order_detail.html', {
        'order': order
    })