# Enhanced Coder Functionality Plan

## Overview

This plan focuses on enhancing the coding capabilities of the Manus-like system, making it more powerful, versatile, and user-friendly. The enhanced coder will be able to generate, execute, debug, and deploy code with minimal user intervention.

## Core Enhancements

### 1. Code Generation Improvements

#### Multi-language Support
- Python (primary)
- JavaScript/TypeScript
- HTML/CSS
- Bash/Shell
- SQL

#### Context-Aware Generation
- Analyze existing codebase for style and patterns
- Maintain consistent naming conventions
- Follow project-specific coding standards
- Consider dependencies and imports

#### Template-Based Generation
- Common design patterns
- Boilerplate reduction
- Framework-specific components (Flask, FastAPI, React, etc.)

### 2. Code Execution System

#### Isolated Execution Environment
- Sandboxed execution to prevent system damage
- Resource limits (CPU, memory, execution time)
- Dependency isolation

#### Real-time Output Streaming
- Stream execution output in real-time
- Support for long-running processes
- Interactive input handling

#### Multi-file Execution
- Execute code across multiple files
- Handle imports and dependencies
- Support for project structures

### 3. Debugging and Testing

#### Automated Error Analysis
- Identify common error patterns
- Suggest fixes for syntax and runtime errors
- Explain errors in plain language

#### Test Generation
- Generate unit tests for functions
- Create integration tests for components
- Support for test-driven development

#### Code Review
- Style checking
- Performance analysis
- Security vulnerability detection
- Best practice recommendations

### 4. Web Development and Deployment

#### Local Development Server
- Automatic setup of development servers
- Hot reloading for web applications
- API endpoint testing

#### FRP Tunnel Integration
- Expose local servers to the internet
- Secure tunneling with authentication
- Custom domain support

#### Static Site Generation
- Generate static websites from templates
- Support for common frameworks (Hugo, Jekyll, etc.)
- Asset optimization

### 5. Interactive Coding Experience

#### Code Completion
- Context-aware suggestions
- Function parameter hints
- Import suggestions

#### Refactoring Tools
- Rename variables/functions
- Extract methods
- Optimize imports
- Code restructuring

#### Visual Feedback
- Syntax highlighting
- Error underlining
- Execution flow visualization

## Implementation Details

### Enhanced Code Generation Tool

```python
@register_tool("generate_code")
def generate_code(
    task_description: str,
    language: str = "python",
    context: str = None,
    existing_code: str = None,
    style_guide: str = None
):
    """
    Generate code based on a task description.
    
    Args:
        task_description: Description of what the code should do
        language: Programming language to use
        context: Additional context about the project
        existing_code: Existing code to build upon
        style_guide: Specific style requirements
        
    Returns:
        Generated code and explanation
    """
    # Prepare prompt with all context
    prompt = f"Generate {language} code for the following task: {task_description}\n\n"
    
    if context:
        prompt += f"Context: {context}\n\n"
    
    if existing_code:
        prompt += f"Existing code:\n```{language}\n{existing_code}\n```\n\n"
    
    if style_guide:
        prompt += f"Style guide: {style_guide}\n\n"
    
    # Add language-specific instructions
    if language == "python":
        prompt += "Follow PEP 8 guidelines. Include docstrings and type hints.\n"
    elif language in ["javascript", "typescript"]:
        prompt += "Follow modern ES6+ syntax. Use proper error handling.\n"
    
    # Generate code using the selected model
    response = generate_text(prompt)
    
    # Extract code and explanation
    # (Implementation depends on model output format)
    
    return {
        "code": extracted_code,
        "explanation": explanation,
        "language": language
    }
```

### Advanced Code Execution Tool

```python
@register_tool("execute_code")
async def execute_code(
    code: str,
    language: str = "python",
    timeout: int = 30,
    stream_output: bool = True,
    environment_vars: dict = None,
    working_directory: str = None,
    dependencies: list = None
):
    """
    Execute code in a controlled environment.
    
    Args:
        code: Code to execute
        language: Programming language
        timeout: Maximum execution time in seconds
        stream_output: Whether to stream output in real-time
        environment_vars: Environment variables to set
        working_directory: Directory to execute in
        dependencies: Dependencies to install
        
    Returns:
        Execution results
    """
    import subprocess
    import tempfile
    import os
    import asyncio
    import time
    from pathlib import Path
    
    # Create temporary directory for execution
    with tempfile.TemporaryDirectory() as temp_dir:
        # Set working directory
        work_dir = working_directory or temp_dir
        os.makedirs(work_dir, exist_ok=True)
        
        # Write code to file
        file_extension = {
            "python": "py",
            "javascript": "js",
            "typescript": "ts",
            "html": "html",
            "css": "css",
            "bash": "sh",
            "sql": "sql"
        }.get(language, "txt")
        
        file_path = Path(work_dir) / f"code.{file_extension}"
        with open(file_path, "w") as f:
            f.write(code)
        
        # Install dependencies if needed
        if dependencies and language == "python":
            for dep in dependencies:
                subprocess.run(["pip", "install", dep], check=True)
        
        # Prepare environment
        env = os.environ.copy()
        if environment_vars:
            env.update(environment_vars)
        
        # Execute based on language
        if language == "python":
            cmd = ["python", str(file_path)]
        elif language in ["javascript", "typescript"]:
            cmd = ["node", str(file_path)]
        elif language == "bash":
            cmd = ["bash", str(file_path)]
        else:
            return {"error": f"Execution not supported for {language}"}
        
        # Execute with timeout and output streaming
        start_time = time.time()
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=work_dir
        )
        
        stdout_chunks = []
        stderr_chunks = []
        
        if stream_output:
            # Stream output in real-time
            async def read_stream(stream, chunks):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    line_str = line.decode('utf-8')
                    chunks.append(line_str)
                    yield line_str
            
            stdout_stream = read_stream(process.stdout, stdout_chunks)
            stderr_stream = read_stream(process.stderr, stderr_chunks)
            
            return {
                "stdout_stream": stdout_stream,
                "stderr_stream": stderr_stream,
                "process": process
            }
        else:
            # Wait for completion
            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout)
                stdout_str = stdout.decode('utf-8')
                stderr_str = stderr.decode('utf-8')
                
                return {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "exit_code": process.returncode,
                    "execution_time": time.time() - start_time
                }
            except asyncio.TimeoutError:
                process.kill()
                return {
                    "error": f"Execution timed out after {timeout} seconds",
                    "stdout": ''.join(stdout_chunks),
                    "stderr": ''.join(stderr_chunks),
                    "execution_time": time.time() - start_time
                }
```

### Website Deployment Tool

```python
@register_tool("deploy_website")
async def deploy_website(
    site_path: str,
    port: int = 8000,
    use_frp: bool = True,
    site_type: str = "static",  # static, flask, fastapi, react
    custom_domain: str = None
):
    """
    Deploy a website locally and optionally expose it via FRP.
    
    Args:
        site_path: Path to the website files
        port: Port to run the server on
        use_frp: Whether to expose via FRP tunnel
        site_type: Type of website
        custom_domain: Custom domain for FRP
        
    Returns:
        Deployment information
    """
    import os
    import subprocess
    import asyncio
    from pathlib import Path
    
    site_dir = Path(site_path)
    
    # Ensure site directory exists
    if not site_dir.exists():
        os.makedirs(site_dir, exist_ok=True)
    
    # Create necessary files based on site type
    if site_type == "static":
        # Create index.html if it doesn't exist
        index_path = site_dir / "index.html"
        if not index_path.exists():
            with open(index_path, "w") as f:
                f.write("<html><body><h1>Site is running!</h1></body></html>")
        
        # Create a simple server
        server_path = site_dir / "server.py"
        with open(server_path, "w") as f:
            f.write(f"""
from http.server import HTTPServer, SimpleHTTPRequestHandler
import os

class CORSRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET')
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        return super().end_headers()

os.chdir('{site_dir}')
httpd = HTTPServer(('0.0.0.0', {port}), CORSRequestHandler)
print(f'Serving at port {port}')
httpd.serve_forever()
            """)
        
        # Start the server
        server_process = subprocess.Popen(["python", str(server_path)])
        
    elif site_type == "fastapi":
        # Create a FastAPI app
        app_path = site_dir / "app.py"
        with open(app_path, "w") as f:
            f.write(f"""
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory if it exists
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    return "<html><body><h1>FastAPI site is running!</h1></body></html>"

@app.get("/api/status")
async def status():
    return {{"status": "ok", "message": "API is operational"}}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port={port})
            """)
        
        # Create static directory
        static_dir = site_dir / "static"
        os.makedirs(static_dir, exist_ok=True)
        
        # Start the server
        server_process = subprocess.Popen(["python", str(app_path)])
    
    # Setup FRP if requested
    frp_url = None
    if use_frp:
        frp_result = await call_tool("setup_frp", local_port=port, custom_domain=custom_domain)
        frp_url = frp_result.get("url")
    
    return {
        "status": "deployed",
        "local_url": f"http://localhost:{port}",
        "frp_url": frp_url,
        "site_type": site_type,
        "site_path": str(site_dir)
    }
```

### Code Review and Improvement Tool

```python
@register_tool("review_code")
async def review_code(
    code: str,
    language: str = "python",
    focus_areas: list = None  # ["style", "performance", "security", "bugs"]
):
    """
    Review code and suggest improvements.
    
    Args:
        code: Code to review
        language: Programming language
        focus_areas: Specific areas to focus on
        
    Returns:
        Review results and suggestions
    """
    if not focus_areas:
        focus_areas = ["style", "performance", "security", "bugs"]
    
    # Prepare prompt for the model
    prompt = f"Review the following {language} code and provide feedback on {', '.join(focus_areas)}:\n\n```{language}\n{code}\n```\n\n"
    
    prompt += "For each issue found, provide:\n"
    prompt += "1. The problematic code snippet\n"
    prompt += "2. An explanation of the issue\n"
    prompt += "3. A suggested fix\n"
    prompt += "4. The category of the issue (style, performance, security, bug)\n\n"
    
    # Add language-specific review guidelines
    if language == "python":
        prompt += "Check for PEP 8 compliance, proper error handling, and efficient algorithms.\n"
    elif language in ["javascript", "typescript"]:
        prompt += "Check for modern ES6+ practices, proper async handling, and security issues like XSS.\n"
    
    # Generate review using the model
    review_text = generate_text(prompt)
    
    # Parse the review into structured format
    # (Implementation depends on model output format)
    
    return {
        "issues_found": parsed_issues,
        "summary": summary,
        "improved_code": improved_code
    }
```

## User Interface for Enhanced Coder

The enhanced coder will have a dedicated interface with the following components:

### Code Editor Panel
- Syntax highlighting
- Line numbers
- Code folding
- Multiple tabs for different files

### Execution Panel
- Run button with options (run, debug, test)
- Real-time output display
- Error highlighting
- Memory and CPU usage monitoring

### Tools Panel
- Code generation
- Code review
- Refactoring
- Testing
- Deployment

### Project Explorer
- File tree view
- Search functionality
- Quick access to recent files

## Integration with Web Deployment

The enhanced coder will seamlessly integrate with the web deployment system:

1. **Development Mode**
   - Local server with hot reloading
   - Real-time preview
   - API testing interface

2. **Deployment Mode**
   - One-click deployment to FRP tunnel
   - Deployment status monitoring
   - Access logs and analytics

3. **Collaboration Features**
   - Shareable links to deployed sites
   - Version control integration
   - Collaborative editing (future enhancement)

## Conclusion

The enhanced coder functionality will transform the Manus-like system into a powerful development environment that can generate, execute, debug, and deploy code with minimal user intervention. By leveraging Google's local models and integrating with web deployment capabilities, the system will provide a comprehensive solution for AI-assisted software development.