import time
import threading
import ollama


MODEL_NAME = "qwen2.5:7b"
chat_history = [{'role': 'system', 'content': "你叫诺诺..."}]

latest_user_input = None
is_running = True
lock = threading.Lock()

def listen_to_user():
    global latest_user_input, is_running
    while True:
        # 1. 这里不需要锁，因为 input 是在等待用户，不涉及共享变量
        i = input() 
        
        # 2. 只有在修改全局变量时，才“瞬时”加锁
        with lock:
            if i == "下次见":
                is_running = False
                break
            if i.strip() != "":
                latest_user_input = i

def ai_brain_loop():
    global latest_user_input, is_running, chat_history
    last_interaction_time = time.time()
    
    print("诺诺已启动，等待你的消息...")

    while True:
        # --- 检查退出标志 ---
        with lock:
            if not is_running: break
        
        current_time = time.time()
        user_text = None

        # --- 第一步：加锁，取走数据，立刻解锁 ---
        with lock:
            if latest_user_input:
                user_text = latest_user_input
                latest_user_input = None # 取走了，清空
                last_interaction_time = current_time

        # --- 第二步：在锁外面处理耗时操作 ---
        if user_text:
            print(f"（听到：{user_text}）")
            # 这里的 chat_history 也要小心，如果要改它，最好也锁一下
            with lock:
                chat_history.append({'role': 'user', 'content': user_text})
            
            # ！！！注意：调用 Ollama 时，没有锁 ！！！
            # 这样 AI 在思考时，用户依然可以打字，listen_to_user 不会被阻塞
            response = ollama.chat(model=MODEL_NAME, messages=chat_history)
            reply = response['message']['content']
            
            with lock:
                chat_history.append({'role': 'assistant', 'content': reply})
            print(f"诺诺: {reply}")

        # --- 第三步：处理自主模式 ---
        elif current_time - last_interaction_time > 30:
            last_interaction_time = current_time # 这只是局部变量，不用锁
            print("（诺诺主动找话题...）")
            
            # 准备数据时锁一下
            with lock:
                temp_history = chat_history + [{'role': 'system', 'content': "（提示：主动挑起话题）"}]
            
            # 调用 Ollama 时不带锁
            response = ollama.chat(model=MODEL_NAME, messages=temp_history)
            reply = response['message']['content']
            
            with lock:
                chat_history.append({'role': 'assistant', 'content': reply})
            print(f"诺诺: {reply}")
            
        time.sleep(0.5) # 频率稍微高一点点

if __name__ == "__main__":
    listener = threading.Thread(target=listen_to_user)
    listener.daemon = True
    listener.start()
    
    ai_brain_loop()