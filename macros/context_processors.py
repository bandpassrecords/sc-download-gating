def cart_count(request):
    """Add cart count to all templates"""
    if request.user.is_authenticated:
        cart = request.session.get('macro_cart', [])
        return {'cart_count': len(cart)}
    return {'cart_count': 0}



