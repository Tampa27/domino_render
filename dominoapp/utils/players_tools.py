import hashlib

def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
def get_device_hash(request):
    ip_address = get_client_ip(request)    
    print('ip: ', ip_address)
        
    if not ip_address:
        return None
    
    # Concatenate the values and create a SHA-256 hash
    texto = f"{ip_address}"
    hash_sha256 = hashlib.sha256(texto.encode()).hexdigest()
    
    return hash_sha256