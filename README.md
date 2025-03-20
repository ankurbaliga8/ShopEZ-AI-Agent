# 🛍️ ShopEZ AI Agent 🚀

### **Automate Your Shopping with AI & Browser Automation!**

ShopEZ AI Agent is an **open-source** AI-powered automation tool that **autonomously** shops for you on Amazon & Walmart. Using **GPT-4o**, **Browser Use**, and **Playwright**, it seamlessly searches for products, adds them to the cart, and completes the checkout—all hands-free!

---

## ✨ Features

✔ **AI-Powered Smart Shopping** – Simply input your shopping list, and the AI categorizes and processes your orders.  
✔ **Autonomous Ordering** – Places Amazon & Walmart orders without manual intervention.  
✔ **Interactive Chatbot** – Built with **React** to handle shopping queries efficiently.  
✔ **Smart List Management** – Uses **GPT-4o** for intelligent categorization (89%+ accuracy).  
✔ **Browser Automation** – Integrates **Browser Use (open-source)** and **Playwright** for checkout automation.

---

## 🏗️ Tech Stack

🔹 **Backend:** FastAPI, LangChain, GPT-4o, Python (3.11 or greater)  
🔹 **Frontend:** React, TailwindCSS, Material UI  
🔹 **Automation:** Playwright, Browser Use (open-source)  
🔹 **Deployment:** Docker, GitHub Actions

---

## 🚀 Installation

### **1️⃣ Clone the Repository**

```sh
git clone https://github.com/ankurbaliga8/ShopEZ-AI-Agent.git
cd ShopEZ-AI-Agent
```

### **🖥️ Backend Setup (FastAPI)**

### **2️⃣ Set Up a Virtual Environment**

```sh
python3 -m venv .venv
source .venv/bin/activate  # Mac/Linux
.venv\Scripts\activate
```

### **3️⃣ Install Dependencies**

```sh
pip install -r requirements.txt
```

### **4️⃣ Set Up Environment Variables**

### Create a .env file and add your API key:

```sh
OPENAI_API_KEY=your_api_key_here
```

### **5️⃣ Run the AI Shopping Agent**

```sh
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### **🖥️ Frontend Setup (React Chatbot)**

### **6️⃣ Navigate to the Frontend Directory**

```sh
cd frontend
```

### **7️⃣ Install Dependencies**

```sh
npm install
```

### **8️⃣ Start the React Development Server**

```sh
npm run dev
```

### **9️⃣ Update API URL (if needed)**

```sh
export const API_URL = "http://localhost:8000";
```
