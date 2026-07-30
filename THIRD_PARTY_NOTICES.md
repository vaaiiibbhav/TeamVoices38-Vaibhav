# Third-Party Notices

## `ui/` — Next.js chat console shell

The layout, ChatKit integration, and base component structure under `ui/`
originate from [openai-cs-agents-demo](https://github.com/openai/openai-cs-agents-demo)
(OpenAI, MIT License). This project replaced its backend entirely (FastAPI +
LangGraph instead of the original Agents SDK demo), repurposed its agent-trace
sidebar into the Inspector panel described in CLAUDE.md, and adapted its
demo-specific copy (page titles, chat prompts, sample greetings) to the campus
helpdesk domain. The original MIT license text is reproduced below, per its
own terms.

```
MIT License

Copyright 2025 OpenAI

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of
the Software, and to permit persons to whom the Software is furnished to do so,
subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

Everything else in this repository — the FastAPI backend, the LangGraph
orchestration graph, the confidence model, the RAG ingestion/retrieval
pipeline, the approval gateway, the Postgres schema, and the admin console —
is original to this project.
