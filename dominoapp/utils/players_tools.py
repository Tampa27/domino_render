import hashlib

def get_client_ip(request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
    
def get_device_hash(request):
    version_string = request.user_agent.os.version_string 
    os = request.user_agent.os.family
    language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    ip_address = get_client_ip(request)
    
    print("OS: ", os)
    print('Version_OS: ', version_string)
    print('language: ', language)
    print('ip: ', ip_address)
        
    if not version_string or not language or not ip_address:
        return None
    
    # Concatenate the values and create a SHA-256 hash
    texto = f"{version_string}{language}{ip_address}"
    hash_sha256 = hashlib.sha256(texto.encode()).hexdigest()
    
    return hash_sha256