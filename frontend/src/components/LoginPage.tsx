// src/components/LoginPage.tsx — Track 5
import { useState } from "react";
import { Shield, Loader2 } from "lucide-react";
import { api, setToken } from "../api/client";
import type { AuthUser } from "../types";

interface Props {
  onLogin: (user: AuthUser) => void;
}

export default function LoginPage({ onLogin }: Props) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError("");
    try {
      const res = await api.login(username, password);
      setToken(res.access_token);
      onLogin({ username, role: res.role, domains: res.domains });
    } catch (err: any) {
      setError(err.message || "Login failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="bg-gray-900 border border-gray-800 rounded-2xl p-10 w-full max-w-md shadow-2xl">
        <div className="flex items-center gap-3 mb-8">
          <Shield className="text-cyan-400" size={32} />
          <div>
            <h1 className="text-2xl font-bold text-white">SENTINEL-MPLS</h1>
            <p className="text-xs text-gray-500">Air-Gapped NetOps Copilot</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-cyan-500"
              placeholder="operator / architect"
              required
            />
          </div>
          <div>
            <label className="text-xs text-gray-400 mb-1 block">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg px-4 py-3 text-white text-sm focus:outline-none focus:border-cyan-500"
              placeholder="••••••••"
              required
            />
          </div>

          {error && <p className="text-red-400 text-xs">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold py-3 rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 size={16} className="animate-spin" /> : <Shield size={16} />}
            {loading ? "Authenticating..." : "Login"}
          </button>
        </form>

        <div className="mt-6 p-3 bg-gray-800 rounded-lg text-xs text-gray-400 space-y-1">
          <p className="font-semibold text-gray-300 mb-2">Default credentials:</p>
          <p><span className="text-cyan-400">operator</span> / operator123 — Read-only (Core + DMZ)</p>
          <p><span className="text-cyan-400">architect</span> / architect123 — Full access (All domains)</p>
        </div>
      </div>
    </div>
  );
}