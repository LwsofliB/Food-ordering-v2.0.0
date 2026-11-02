# start_kitchen.py
import multiprocessing as mp
import os
import json as j
from datetime import datetime

_order_queue = None
_manager = None
_kitchen_active_orders = None

def init_shared_orders():
    global _manager, _kitchen_active_orders
    if _manager is None:
        _manager = mp.Manager()
        _kitchen_active_orders = _manager.list()

def get_order_queue():
    global _order_queue
    if _order_queue is None:
        _order_queue = mp.Queue()
    return _order_queue

def _append_json_log(order_data):
    # ★ 修复：改成相对路径，跨平台兼容
    log_file = '订单日志.json'
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            logs = j.load(f)
    except (FileNotFoundError, j.JSONDecodeError):
        logs = []
    logs.append(order_data)
    with open(log_file, 'w', encoding='utf-8') as f:
        j.dump(logs, f, ensure_ascii=False, indent=2)

def _append_txt_log(order_data):
    # ★ 修复：改成相对路径
    txt_file = '订单日志.txt'
    with open(txt_file, 'a', encoding='utf-8') as f:
        f.write(f"\n===== Orders #{order_data['order_no']} =====\n")
        f.write(f"时间: {order_data['time']}\n")
        for num, dish in enumerate(order_data['dishes'], start=1):
            f.write(f"{num}: {dish['dish_name']} --> {dish['dish_amount']}份 "
                    f"(¥{dish['dish_price']} x {dish['dish_amount']})\n")
        f.write(f"合计: ¥{order_data['total_price']}\n")

def _handle_order(order_package):
    global _kitchen_active_orders
    
    order_no = order_package['order_no']
    dish_list = order_package['dishes']
    
    total = sum(d['dish_price'] * d['dish_amount'] for d in dish_list)
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    order_data = {
        'order_no': order_no,
        'time': now_str,
        'dishes': dish_list,
        'total_price': total,
        'status': 'pending'
    }

    print(f"\n========== 后厨小票 #{order_no} ==========")
    for num, d in enumerate(dish_list, start=1):
        sub = d['dish_price'] * d['dish_amount']
        print(f"{num}. {d['dish_name']}  ¥{d['dish_price']} x {d['dish_amount']} = ¥{sub}")
    print(f"合计: ¥{total}")
    print("==============================\n")

    _append_json_log(order_data)
    _append_txt_log(order_data)
    _kitchen_active_orders.append(order_data)

def kitchen_worker(q, active_orders):
    global _kitchen_active_orders
    _kitchen_active_orders = active_orders
    print(f"[后厨进程 PID={os.getpid()}] 已启动，等待订单...")
    while True:
        package = q.get()
        if package is None:
            break
        _handle_order(package)

def start_kitchen():
    init_shared_orders()
    q = get_order_queue()
    p = mp.Process(target=kitchen_worker, args=(q, _kitchen_active_orders), daemon=True)
    p.start()
    return p

def get_kitchen_orders():
    if _kitchen_active_orders is None:
        return []
    return list(_kitchen_active_orders)

def complete_order(order_no):
    if _kitchen_active_orders is None:
        return False
        
    found = False
    for i, o in enumerate(_kitchen_active_orders):
        # ★ 关键：必须把两边的类型都转成字符串比较，防止 "123" != 123
        if str(o['order_no']) == str(order_no):
            del _kitchen_active_orders[i]
            found = True
            break
            
    return found