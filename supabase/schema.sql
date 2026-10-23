-- Run only in a dedicated development Supabase project first.
create extension if not exists pgcrypto;

create table if not exists public.ocr_documents (
    id uuid primary key default gen_random_uuid(),
    created_at timestamptz not null default now(),
    source_filename text not null,
    source_type text,
    extracted_text text not null default '',
    ocr_result jsonb not null default '{}'::jsonb,
    average_confidence numeric(6,5),
    status text not null default 'processed'
        check (status in ('queued', 'processed', 'needs_review', 'failed')),
    workflow_execution_id text,
    idempotency_key text unique,
    error_message text
);

create index if not exists ocr_documents_created_at_idx
    on public.ocr_documents (created_at desc);
create index if not exists ocr_documents_status_idx
    on public.ocr_documents (status);

alter table public.ocr_documents enable row level security;

-- No public policies are created by this starter.
-- Insert from a trusted n8n/server-side credential only.
-- Add narrowly scoped policies only after defining your app's authentication model.
