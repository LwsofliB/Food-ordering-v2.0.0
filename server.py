# server.py
from flask import Flask, request, jsonify, render_template
import json
import threading
import uuid
from start_kitchen import get_order_queue, start_kitchen, get_kitchen_orders, complete_order

app = Flask(__name__)
file_lock = threading.Lock()

# ★ 修复：改成相对路径
MENU_FILE = '菜品数据.json'

def read_menu():
    with file_lock:
        try:
            with open(MENU_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

def save_menu(data):
    with file_lock:
        with open(MENU_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

@app.route('/order')
def page_order():
    return render_template('order.html')

@app.route('/kitchen')
def page_kitchen():
    return render_template('kitchen.html')

@app.route('/admin')
def page_admin():
    return render_template('admin.html')

@app.route('/api/menu', methods=['GET'])
def api_menu():
    return jsonify(read_menu())

@app.route('/api/order', methods=['POST'])
def api_order():
    data = request.get_json()
    if not data or 'dishes' not in data: return jsonify({'status': 'error'}), 400
    
    menu = read_menu()
    menu_map = {d['dish_name']: d['dish_price'] for d in menu}
    
    cleaned = []
    for item in data['dishes']:
        name = item.get('dish_name')
        amount = item.get('dish_amount', 0)
        if name in menu_map and 0 < amount <= 10:
            cleaned.append({'dish_name': name, 'dish_price': menu_map[name], 'dish_amount': amount})
            
    if not cleaned: return jsonify({'status': 'error', 'msg': '无有效菜品'}), 400

    order_no = str(uuid.uuid4()).replace('-', '')[:6].upper()
    
    order_package = {'order_no': order_no, 'dishes': cleaned}
    get_order_queue().put(order_package)  
    
    return jsonify({'status': 'ok', 'order_no': order_no})

@app.route('/api/kitchen/orders', methods=['GET'])
def api_kitchen_orders():
    return jsonify(get_kitchen_orders())

@app.route('/api/kitchen/complete', methods=['POST'])
def api_kitchen_complete():
    try:
        data = request.get_json()
        print(f"\n[DEBUG] 收到完成请求，数据: {data}")  # ★ 打印看看收到了什么
        
        if not data or 'order_no' not in data:
            print("[DEBUG] 错误：缺少 order_no")
            return jsonify({'status': 'error', 'msg': 'missing order_no'}), 400
            
        order_no = data.get('order_no')
        result = complete_order(order_no)
        
        if result:
            print(f"[DEBUG] 订单 #{order_no} 已成功从看板移除！")
            return jsonify({'status': 'ok'})
        else:
            print(f"[DEBUG] 错误：后厨列表里找不到订单 #{order_no}")
            return jsonify({'status': 'error', 'msg': 'order not found'}), 404
            
    except Exception as e:
        print(f"[DEBUG] 服务器异常: {e}")
        return jsonify({'status': 'error', 'msg': str(e)}), 500

@app.route('/api/admin/add', methods=['POST'])
def api_admin_add():
    data = request.json
    menu = read_menu()
    menu.append({'dish_name': data['name'], 'dish_price': int(data['price'])})
    save_menu(menu)
    return jsonify({'status': 'ok'})

@app.route('/api/admin/delete', methods=['POST'])
def api_admin_delete():
    name = request.json.get('name')
    menu = read_menu()
    menu = [d for d in menu if d['dish_name'] != name]
    save_menu(menu)
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    start_kitchen()
    app.run(host='0.0.0.0', port=5000, threaded=True)