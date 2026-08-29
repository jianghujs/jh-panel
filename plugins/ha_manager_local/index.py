# coding: utf-8

import sys

if __name__ == '__main__' and len(sys.argv) > 1 and sys.argv[1] == 'status':
    print('start')
    sys.exit(0)

def status():
    return 'start'

def _result(status, msg, data=None):
    return '{"status":%s,"msg":%s,"data":%s}' % (
        'true' if status else 'false',
        repr(msg),
        repr(data if data is not None else {})
    )

def get_state():
    state = {
        'role': 'standby',
        'desired_role': 'standby',
        'switch_status': 'idle',
        'health_status': 'normal',
        'health_text': '正常',
        'step': 'idle',
        'step_list': [],
        'last_action': ''
    }
    print(_result(True, 'ok', state))

def title_state():
    print(_result(True, 'ok', {'installed': True, 'role': 'standby', 'desired_role': 'standby', 'switch_status': 'idle'}))

if __name__ == '__main__':
    func = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if func == 'status':
        print(status())
    elif func == 'get_state':
        get_state()
    elif func == 'title_state':
        title_state()
    else:
        print('error')
