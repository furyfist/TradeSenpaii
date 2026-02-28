// src/lib/supabase.js
// Single shared Supabase client — import this everywhere instead of calling createClient() directly.
import { createClient } from "@supabase/supabase-js";

export const supabase = createClient(
    import.meta.env.VITE_SUPABASE_URL,
    import.meta.env.VITE_SUPABASE_ANON_KEY
);
