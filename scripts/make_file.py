import sys, base64
if len(sys.argv) > 2:
    open(sys.argv[1], 'wb').write(base64.b64decode(sys.argv[2]))
    print(f'Written {sys.argv[1]}')
