from python_app.brokers.registry import PROVIDER_INFO
import os

print('Total entries:', len(PROVIDER_INFO))

# Count by api_status
stubs = sum(1 for v in PROVIDER_INFO.values() if v['api_status'] == 'stub')
verified = sum(1 for v in PROVIDER_INFO.values() if v['api_status'] == 'verified')
live = sum(1 for v in PROVIDER_INFO.values() if v['api_status'] == 'live')
deprecated = sum(1 for v in PROVIDER_INFO.values() if v['api_status'] == 'deprecated')
print(f'Stub: {stubs}, Verified: {verified}, Live: {live}, Deprecated: {deprecated}')

# Check some entries
for k in ['zuari_finserv', 'hdfc_bank', '_21artha', '5paisa_capital', 'zerodha']:
    if k in PROVIDER_INFO:
        name = PROVIDER_INFO[k]['name']
        status = PROVIDER_INFO[k]['api_status']
        impl = PROVIDER_INFO[k]['_implementation']
        stub_path = 'python_app/brokers/' + impl
        stub_exists = os.path.exists(stub_path)
        print(f'OK {k}: name={name}, status={status}, stub_exists={stub_exists}')
    else:
        print(f'MISSING: {k}')