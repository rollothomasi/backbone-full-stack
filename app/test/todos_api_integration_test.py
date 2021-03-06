import json
import requests
import unittest
from pymongo import Connection
from bson.objectid import ObjectId
from multiprocessing import Process
from app.server import app

port = 5001
url = 'http://localhost:%s' % port
db_name = 'todos_test'

def start_server():
    app.conn_args = {}
    app.db_name = db_name
    app.debug = False
    app.run(port=port)

def send_data(method, path, data):
    return requests.request(method, url + path, data=json.dumps(data), 
        headers={'Content-Type': 'application/json'})

class TodoApiIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server_process = Process(target=start_server)
        cls.server_process.start()
        cls.conn = Connection('localhost', 27017)
    
    @classmethod
    def tearDownClass(cls):
        cls.server_process.terminate()
        cls.conn.drop_database(db_name)
        cls.conn.disconnect()
    
    def tearDown(self):
        self.conn[db_name].drop_collection('todos')
    
    def test_create_todo(self):
        expected_todo = {'text': 'foo', 'order': 1, 'done': False}
        
        resp = send_data('post','/todos/', expected_todo)
        
        self.assertEqual(200, resp.status_code)
        
        actual_todo = json.loads(resp.content)
        
        self.assertIn('id', actual_todo)
        
        _id = actual_todo['id']
        del actual_todo['id']
        
        self.assertEqual(expected_todo, actual_todo)
        
        todo = self.conn[db_name].todos.find_one({'_id': ObjectId(_id)})
        
        self.assertIsNotNone(todo)
    
    def test_get_all_todos(self):
        send_data('post','/todos/', {'text': 'foo', 'order': 3, 'done': False})
        send_data('post','/todos/', {'text': 'bar', 'order': 1, 'done': False})
        send_data('post','/todos/', {'text': 'baz', 'order': 2, 'done': False})
        
        resp = requests.get(url + '/todos/')
        
        self.assertEqual(200, resp.status_code)
        
        data = json.loads(resp.content)
        
        self.assertEqual(3, len(data))
        
        last_order = 0
        
        for todo in data:
            self.assertIn('id', todo)
            self.assertIsNotNone(todo['id'])
            self.assertGreater(todo['order'], last_order)
            last_order = todo['order']
    
    def test_get_todo(self):
        todo = {'text': 'foo', 'order': 1, 'done': False}
        create_resp = send_data('post', '/todos/', todo)
        _id = json.loads(create_resp.content)['id']
        
        resp = requests.get(url + '/todos/' + _id)
        
        self.assertEqual(200, resp.status_code)
        
        data = json.loads(resp.content)
        
        self.assertEqual(_id, data['id'])
        self.assertEqual(data['text'], todo['text'])
        self.assertEqual(data['order'], todo['order'])
        self.assertEqual(data['done'], todo['done'])
    
    def test_update_todo(self):
        todo = {'text': 'foo', 'order': 1, 'done': False}
        create_resp = send_data('post','/todos/', todo)
        
        _id = json.loads(create_resp.content)['id']
        
        todo['text'] = 'bar'
        
        update_resp = send_data('put', '/todos/' + _id, todo)
        
        self.assertEqual(200, update_resp.status_code)
        
        resp = requests.get(url + '/todos/' + _id)
        data = json.loads(resp.content)
        
        self.assertEqual(data['text'], todo['text'])
        self.assertEqual(data['order'], todo['order'])
        self.assertEqual(data['done'], todo['done'])
    
    def test_delete_todo(self):
        todo = {'text': 'foo', 'order': 1, 'done': False}
        create_resp = send_data('post','/todos/', todo)
        
        _id = json.loads(create_resp.content)['id']
        
        delete_resp = requests.delete(url + '/todos/' + _id)
        
        self.assertEqual(200, delete_resp.status_code)
        
        resp = requests.get(url + '/todos/' + _id)
        
        self.assertEqual(404, resp.status_code)
    
    def test_that_non_existant_todo_should_return_404(self):
        resp = requests.get(url + '/todos/4e971ed699b6bd4f08000001')
        
        self.assertEqual(404, resp.status_code)
    
    def test_that_invalid_todo_id_should_return_400(self):
        resp = requests.get(url + '/todos/123')
        
        self.assertEqual(400, resp.status_code)
    
    def test_invalid_method_should_return_not_allowed(self):
        resp = requests.request('put', url + '/todos/')

        self.assertEqual(405, resp.status_code)
