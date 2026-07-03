// frontend/src/api/client.ts
import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
});
