export type User = {
  id: string;
  name: string;
  demo: boolean;
  institution_access: boolean;
};
export type Doc = {
  id: string;
  name: string;
  size: number;
  status: string;
  error: string;
  method: string;
  created: number;
  pages: number;
  pending: number;
  fact_count: number;
  extension: string;
};
export type Fact = {
  id: string;
  document_id: string;
  category: string;
  value: string;
  quote: string;
  page: number;
  location: string;
  status: string;
  scheduled_date: string | null;
  scheduled_time: string | null;
  conflict: boolean;
  note: string;
  version: number;
};
export type Task = {
  id: string;
  fact_id: string;
  title: string;
  due_date: string;
  due_time: string | null;
  category: string;
  status: string;
  active: boolean;
  version: number;
};
export type Workspace = {
  user: User;
  documents: Doc[];
  facts: Fact[];
  tasks: Task[];
};
export type Citation = {
  id: string;
  title: string;
  publisher: string;
  url: string;
  text: string;
  reviewed_at: string;
  source_type?: "personal" | "knowledge";
  document_id?: string | null;
  page?: number | null;
  location?: string;
  review_status?: string;
};
export type Message = {
  id: string;
  role: string;
  text: string;
  citations: Citation[];
  status: string;
};
export type Source = {
  id: string;
  name: string;
  method: string;
  pages: { page: number; text: string; location: string; ocr: boolean }[];
};
export type Simulation = {
  id: string;
  name: string;
  inputs: Record<string, number | string | boolean>;
  results: Record<string, number | string | null>;
  analysis: {
    provenance?: Record<
      string,
      {
        approval_id?: string;
        source_id?: string;
        kind?: string;
        value?: number;
      }
    >;
    scenarios: Record<string, number | string | null>[];
    sensitivity: Record<string, number | string>[];
  };
};
let csrf = "";
export function setCsrf(value: string) {
  csrf = value;
}
export class APIError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  if (init.method && init.method !== "GET") headers.set("X-CSRF-Token", csrf);
  const response = await fetch("/api" + path, {
    ...init,
    headers,
    credentials: "same-origin",
  });
  if (!response.ok) {
    let message = "暂时无法完成，请稍后重试。";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
      else if (Array.isArray(data.detail))
        message = "请检查填写内容是否完整、格式是否正确。";
    } catch {
      /* no raw server response */
    }
    throw new APIError(message, response.status);
  }
  return response.json() as Promise<T>;
}
export type StreamEvent =
  | { type: "status"; message: string }
  | { type: "delta"; text: string }
  | { type: "done"; id: string; citations: Citation[]; status: string }
  | { type: "error"; message: string };

export async function streamInstitution<T>(path:string,body?:unknown):Promise<T>{
  const response=await fetch('/api/institution'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},...(body===undefined?{}:{body:JSON.stringify(body)})});
  if(!response.ok||!response.body)throw new APIError('暂时无法处理，请稍后重试。',response.status);
  const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
  try{
    while(true){const {done,value}=await reader.read();buffer+=decoder.decode(value,{stream:!done});const lines=buffer.split('\n');buffer=lines.pop()||'';
      for(const line of lines){if(!line.trim())continue;const event=JSON.parse(line);if(event.type==='error')throw new APIError(event.message,event.status);if(event.type==='result')return event.data as T;}
      if(done)break;
    }
    throw new Error('连接中断，请查看历史记录，若尚未完成可重新提交。');
  }finally{await reader.cancel().catch(()=>{});reader.releaseLock();}
}

export async function streamQuestion(
  question: string,
  onEvent: (event: StreamEvent) => void,
): Promise<void> {
  const response = await fetch("/api/messages/stream", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf },
    body: JSON.stringify({ question }),
  });
  if (!response.ok || !response.body) {
    let message = "暂时无法完成，请稍后重试。";
    try {
      const data = await response.json();
      if (typeof data.detail === "string") message = data.detail;
    } catch {
      // Keep the safe generic message.
    }
    throw new APIError(message, response.status);
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value, { stream: !done });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";
    for (const line of lines)
      if (line.trim()) onEvent(JSON.parse(line) as StreamEvent);
    if (done) break;
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer) as StreamEvent);
}
export function today() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}
export function shortDate(day: string) {
  const d = new Date(day + "T12:00:00");
  return `${d.getMonth() + 1}月${d.getDate()}日`;
}
