# traffic_collector.py
from flask import Flask, request, jsonify

import csv
import os
import threading
import time
import json
from datetime import datetime
from collections import defaultdict
from queue import Queue
import hashlib
import base64

app = Flask(__name__)


class TrafficCollector:
    
    def __init__(self, output_dir="./traffic_data"):
        self.output_dir = output_dir
        self.data_queue = Queue(maxsize=10000)
        self.writers = {}
        self.lock = threading.Lock()
        self.flush_interval = 10  # 10秒刷新一次
        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        
        # 启动处理线程
        self.processor_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.processor_thread.start()
        
        # 初始化CSV文件
        self._init_csv_files()
    
    def _init_csv_files(self):
        """初始化CSV文件结构"""
        csv_structure = {
            'headers': [
                'timestamp', 'method', 'uri', 'query_string',
                'content_type', 'content_length', 'headers_base64', 'body_json_base64',
                'user_agent', 'client_ip', 'request_id'
            ]
        }
        
        config_file = os.path.join(self.output_dir, 'csv_config.json')
        with open(config_file, 'w') as f:
            json.dump(csv_structure, f, indent=2)
    
    def _encode_to_base64(self, data):
        """将数据编码为base64字符串"""
        if not data:
            return ''
        
        try:
            if isinstance(data, (dict, list)):
                # 如果是JSON对象，先序列化为JSON字符串
                json_str = json.dumps(data, ensure_ascii=False)
                return base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
            elif isinstance(data, str):
                return base64.b64encode(data.encode('utf-8')).decode('utf-8')
            elif isinstance(data, bytes):
                return base64.b64encode(data).decode('utf-8')
            else:
                # 其他类型尝试转换为字符串
                return base64.b64encode(str(data).encode('utf-8')).decode('utf-8')
        except Exception as e:
            print(f"Base64编码失败: {e}")
            return ''
    
    def _parse_json_body(self, body_text):
        """尝试解析JSON body"""
        if not body_text or not isinstance(body_text, str):
            return None
        
        try:
            # 尝试解析JSON
            json_obj = json.loads(body_text)
            return json_obj
        except json.JSONDecodeError:
            # 如果不是有效的JSON，返回None
            return None
        except Exception as e:
            print(f"JSON解析失败: {e}")
            return None
    
    def collect_request(self, req_data):
        """收集请求数据"""
        self.data_queue.put(req_data)
    
    def _get_csv_filename(self, uri):
        """根据URI生成CSV文件名"""
        # 清理URI，去掉特殊字符
        safe_uri = uri.strip('/').replace('/', '_').replace('?', '_').replace('&', '_')
        if len(safe_uri) > 100:  # 限制文件名长度
            safe_uri = hashlib.md5(safe_uri.encode()).hexdigest()[:20]
        
        if not safe_uri:
            safe_uri = 'default'
        
        return f"{safe_uri}.csv"
    
    def _get_csv_writer(self, uri):
        """获取或创建CSV写入器"""
        with self.lock:
            if uri not in self.writers:
                filename = self._get_csv_filename(uri)
                filepath = os.path.join(self.output_dir, filename)
                
                # 检查文件是否存在，决定是否写入表头
                write_header = not os.path.exists(filepath)
                
                csv_file = open(filepath, 'a', newline='', encoding='utf-8')
                writer = csv.writer(csv_file)
                
                if write_header:
                    writer.writerow([
                        'timestamp', 'method', 'uri', 'query_string',
                        'content_type', 'content_length', 'headers_base64', 'body_json_base64',
                        'user_agent', 'client_ip', 'request_id'
                    ])
                
                self.writers[uri] = {
                    'file': csv_file,
                    'writer': writer,
                    'last_flush': time.time()
                }
            
            return self.writers[uri]
    
    def _process_queue(self):
        """处理队列中的数据"""
        batch_size = 100
        batch = []
        
        while True:
            try:
                # 从队列获取数据，每1s检查一次
                req_data = self.data_queue.get(timeout=1)
                batch.append(req_data)
                
                # 达到批量大小或超时，写入文件
                if len(batch) >= batch_size or self.data_queue.empty():
                    self._write_batch(batch)
                    batch = []
            
            except Exception as e:
                if batch:
                    self._write_batch(batch)
                    batch = []
                time.sleep(0.1)
    
    def _write_batch(self, batch):
        """批量写入数据"""
        uri_groups = defaultdict(list)
        
        # 按URI分组
        for req_data in batch:
            uri = req_data.get('uri', 'default')
            uri_groups[uri].append(req_data)
        
        # 分别写入不同的CSV文件
        for uri, requests in uri_groups.items():
            writer_info = self._get_csv_writer(uri)
            writer = writer_info['writer']
            
            for req in requests:
                writer.writerow([
                    req.get('timestamp', datetime.now().isoformat()),
                    req.get('method', 'GET'),
                    req.get('uri', ''),
                    req.get('query_string', ''),
                    req.get('content_type', ''),
                    req.get('content_length', 0),
                    req.get('headers_base64', ''),
                    req.get('body_json_base64', ''),
                    req.get('user_agent', ''),
                    req.get('client_ip', ''),
                    req.get('request_id', '')
                ])
            
            # 定期刷新文件，每10s刷新一次
            if time.time() - writer_info['last_flush'] > self.flush_interval:
                writer_info['file'].flush()
                writer_info['last_flush'] = time.time()
    
    def close(self):
        """关闭所有文件"""
        with self.lock:
            for writer_info in self.writers.values():
                writer_info['file'].close()
            self.writers.clear()


# 全局收集器实例
collector = TrafficCollector()


@app.route('/stats', methods=['GET'])
def get_stats():
    """获取统计信息"""
    traffic_dir = collector.output_dir
    files = os.listdir(traffic_dir)
    csv_files = [f for f in files if f.endswith('.csv')]
    
    stats = {}
    for csv_file in csv_files:
        filepath = os.path.join(traffic_dir, csv_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            row_count = sum(1 for row in reader) - 1  # 减去表头
        
        stats[csv_file] = {
            'records': row_count,
            'size': os.path.getsize(filepath)
        }
    
    return jsonify({
        'total_files': len(csv_files),
        'total_records': sum(s['records'] for s in stats.values()),
        'files': stats
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    })


@app.route('/decode/base64', methods=['POST'])
def decode_base64():
    """解码base64数据接口（用于测试和调试）"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        encoded_data = data.get('data')
        if not encoded_data:
            return jsonify({'error': 'No data field provided'}), 400
        
        # 解码base64
        try:
            decoded_bytes = base64.b64decode(encoded_data)
            
            # 尝试解码为UTF-8文本
            try:
                decoded_text = decoded_bytes.decode('utf-8')
                
                # 尝试解析为JSON
                try:
                    json_obj = json.loads(decoded_text)
                    return jsonify({
                        'decoded': decoded_text,
                        'json': json_obj
                    })
                except json.JSONDecodeError:
                    return jsonify({
                        'decoded': decoded_text,
                        'is_json': False
                    })
            
            except UnicodeDecodeError:
                return jsonify({
                    'decoded': 'Binary data (cannot decode as UTF-8)',
                    'base64_decoded': base64.b64encode(decoded_bytes).decode('utf-8'),
                    'size_bytes': len(decoded_bytes)
                })
        
        except Exception as e:
            return jsonify({'error': f'Base64 decode error: {str(e)}'}), 400
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'])
def collect(path):
    """收集请求数据的接口"""
    try:
        # 获取请求body
        body_data = request.get_data()
        body_text = ''
        json_body = None
        
        # 尝试解码body为文本
        try:
            body_text = body_data.decode('utf-8')
        except UnicodeDecodeError:
            # 如果是二进制数据，保持为base64
            body_text = ''
        
        # 尝试解析JSON body
        if body_text:
            json_body = collector._parse_json_body(body_text)
        
        # 提取请求信息
        req_data = {
            'timestamp': datetime.now().isoformat(),
            'method': request.method,
            'uri': request.path,
            'query_string': request.query_string.decode('utf-8') if request.query_string else '',
            'content_type': request.content_type or '',
            'content_length': request.content_length or 0,
            # 'headers': dict(request.headers),
            'headers_base64': collector._encode_to_base64(dict(request.headers)),
            # 'body': body_text,
            # 'body_base64': base64.b64encode(body_data).decode('utf-8') if body_data else '',
            'body_json_base64': collector._encode_to_base64(json_body) if json_body else '',
            'user_agent': request.headers.get('User-Agent', ''),
            'client_ip': request.remote_addr,
            'request_id': request.headers.get('X-Request-ID', '')
        }
        
        # 异步收集
        collector.collect_request(req_data)
        
        return jsonify({'status': 'success', 'message': 'Request collected'})
    
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


if __name__ == '__main__':
    try:
        app.run(host='0.0.0.0', port=8888, threaded=True)
    finally:
        collector.close()
