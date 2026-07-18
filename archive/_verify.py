from python_app.brokers.registry import PROVIDER_INFO, get_provider
print('PROVIDER_INFO count:', len(PROVIDER_INFO))
print('get_provider callable:', callable(get_provider))

# Test get_provider
try:
    stub = get_provider('zuari_finserv')
    print('get_provider(zuari_finserv):', type(stub).__name__)
except Exception as e:
    print('ERROR get_provider:', e)

# Verify entries
for k in ['zerodha', 'zuari_finserv', '_21artha', '5paisa_capital', 'icici', 'hdfc_bank']:
    if k in PROVIDER_INFO:
        info = PROVIDER_INFO[k]
        status = info['api_status']
        name = info['name']
        impl = info['_implementation']
        print(f'OK {k}: name={name}, status={status}')
    else:
        print(f'MISSING: {k}')