
# 🧭 **Frontend Implementation Plan – GSSR Knowledge Graph Dashboard**

**Stack:**

* **Framework:** Next.js 14 (App Router)
* **UI Library:** [shadcn/ui](https://ui.shadcn.com)
* **Styling:** Tailwind CSS
* **Icons:** Lucide React
* **State Management:** React Query or SWR
* **Build Tool:** Vite or Next.js (recommended Next.js for SSR-ready)

---

## 🧩 **Core Objective**

Implement a responsive dashboard that visualizes and monitors the full GSSR flow:
**Upload → Process → Monitor → Query.**

All UI should leverage **Shadcn components**, **not custom-built ones**, unless absolutely necessary.

---

## ✅ **1. Setup Phase**

### TODOs

* [ ] Scaffold Next.js project:

  ```bash
  npx create-next-app gssr-frontend
  cd gssr-frontend
  ```
* [ ] Install and configure Shadcn UI:

  ```bash
  npx shadcn@latest init
  ```
* [ ] Add components:

  ```bash
  npx shadcn@latest add button card progress accordion alert input scroll-area badge spinner resizable
  ```
* [ ] Install dependencies:

  ```bash
  npm install lucide-react @tanstack/react-query axios
  ```
* [ ] Configure Tailwind (colors, dark mode, container spacing).
* [ ] Create `.env.local` → define `APP_API_GATEWAY_URL`.

---

## 🗂️ **2. Folder Structure**

```
src/
 ├─ app/
 │   ├─ page.tsx                 # Main Dashboard
 │   ├─ api/                     # (Optional) API proxy routes
 │   └─ globals.css
 ├─ components/
 │   ├─ document-list.tsx
 │   ├─ document-status-panel.tsx
 │   ├─ upload-button.tsx
 │   ├─ live-log.tsx
 │   ├─ chat-input.tsx
 │   ├─ layout/
 │   │   ├─ resizable-panels.tsx
 │   └─ ui/                      # Shadcn generated components
 ├─ lib/
 │   ├─ api.ts                   # Axios API client
 │   ├─ types.ts                 # Type definitions
 │   └─ utils.ts
 └─ hooks/
     └─ useDocumentStatus.ts     # Polling & live status updates
```

---

## ⚙️ **3. API Integration Plan**

Based on your shell script, we have these main endpoints:

| Function                | HTTP | Endpoint                               | UI Integration                         |
| ----------------------- | ---- | -------------------------------------- | -------------------------------------- |
| Request upload URL      | POST | `/upload`                              | Triggered by **“+ New Upload” Button** |
| Check processing status | GET  | `/status/{job_id}`                     | Polled by **Document Status Panel**    |
| Query for answer        | POST | `/query`                               | Connected to **Chat Input Bar**        |
| Logs (optional)         | GET  | `/logs/{job_id}` or from Dynamo tables | Used for **Live Log** view             |

**Example Axios client:**

```ts
const api = axios.create({
  baseURL: process.env.APP_API_GATEWAY_URL,
});

export const uploadFile = async (filename: string) =>
  (await api.post("/upload", { filename })).data;

export const getStatus = async (jobId: string) =>
  (await api.get(`/status/${jobId}`)).data;

export const runQuery = async (query: string) =>
  (await api.post("/query", { query })).data;
```

---

## 🎨 **4. Component Breakdown (Using Shadcn Components)**

### **Left Panel – Document List**

* `ResizablePanel` (from Shadcn)
* `ScrollArea` for overflow
* `Button` (`+ New Upload`)
* `Card` for document items
* `Spinner` beside active document name
* Highlight selected doc with `bg-primary/10 border-primary text-primary`

### **Right Panel – Document Status**

* `Card` for progress stats
* `Progress` for percentage completion
* `Accordion` + `ScrollArea` for “Live Log”
* `Badge` for stage label (e.g., D1, D2a, D2b)
* `Alert` for status info
* `Input` + `Button` (disabled until processing completes)

---

## 🔁 **5. Functional Logic**

| Feature               | Description                                              | Implementation                      |
| --------------------- | -------------------------------------------------------- | ----------------------------------- |
| Upload document       | Select and send filename to `/upload`                    | Show upload spinner → Save `job_id` |
| Poll processing       | Use React Query’s `useQuery` with `refetchInterval=5000` | Update `Progress` bar and logs      |
| Display LLM call logs | Render `Accordion` → `ScrollArea` with `Badge`           | Map pipeline stages to badge colors |
| Handle query          | Enable chat input after status=“completed”               | Show loading `Spinner` on submit    |
| Render response       | Display `answer` and `references`                        | (Optional future feature)           |

---

## 🧠 **6. Developer TODO Checklist**

### **Initial Setup**

* [ ] Initialize project, Tailwind, and Shadcn UI
* [ ] Add `.env.local` with `APP_API_GATEWAY_URL`
* [ ] Configure Lucide icons

### **UI Components**

* [ ] Create layout with `Resizable` for left/right panels
* [ ] Implement document list (with selection + spinner)
* [ ] Add “New Upload” modal (optional: Shadcn `Dialog`)
* [ ] Implement right panel with `Progress` + `Accordion` logs
* [ ] Add disabled `Input` + `Button` for chat bar
* [ ] Add `Alert` for “Chat will be enabled…”

### **API Hooks**

* [ ] `useUpload()` – handle POST `/upload` and S3 upload step
* [ ] `useStatus(jobId)` – poll `/status/{job_id}`
* [ ] `useQueryLLM()` – handle `/query`

### **State Flow**

* [ ] Store current job ID in React state or Context
* [ ] Reset UI when new upload starts
* [ ] Enable chat bar only when status === `"completed"`

---

## 🔍 **7. Future Enhancements**

* [ ] Add dark/light theme toggle (`ThemeProvider` from Shadcn)
* [ ] Add toast notifications for upload success/error
* [ ] Add persisted history of uploaded documents
* [ ] Integrate “network graph view” (e.g., via D3.js or Cytoscape.js)

---

## 🧾 **8. Deliverables**

✅ Fully functional Shadcn-based frontend that:

* Uploads a text file → triggers backend flow
* Displays live progress, log stream, and pipeline stages
* Unlocks chat bar once processing is complete
* Uses **only official Shadcn components** (no custom spinners, alerts, or inputs)

---

