# Advanced Features Implementation Plan

This document outlines the plan for implementing advanced features that are currently missing or need improvement in the Google Manus System.

## 1. Streaming Response Enhancements

### Current Limitations
- Basic streaming implementation lacks proper error handling
- No visual feedback during streaming in the UI
- Limited support for streaming in the API endpoints
- No way to interrupt long-running streams

### Implementation Plan

#### 1.1 Robust Streaming Core
```python
async def stream_with_error_handling(prompt, model_type=None, model_name=None, timeout=60):
    """Stream responses with proper error handling and timeout."""
    try:
        # Start a timeout task
        timeout_task = asyncio.create_task(asyncio.sleep(timeout))
        
        # Start the streaming task
        stream_task = asyncio.create_task(
            model_adapter.generate_response(prompt, model_type, model_name, stream=True)
        )
        
        # Wait for either task to complete
        done, pending = await asyncio.wait(
            [stream_task, timeout_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel the pending task
        for task in pending:
            task.cancel()
        
        # If the timeout task completed first, the stream task timed out
        if timeout_task in done:
            raise TimeoutError(f"Streaming response timed out after {timeout} seconds")
        
        # Get the stream result
        stream_result, confidence = stream_task.result()
        
        # Return the stream with error handling wrapper
        async for chunk in stream_result:
            yield chunk, None  # (chunk, error)
            
    except asyncio.CancelledError:
        yield None, "Stream was cancelled"
    except TimeoutError as e:
        yield None, str(e)
    except Exception as e:
        yield None, f"Error during streaming: {str(e)}"
```

#### 1.2 UI Streaming Improvements
```python
async def on_chat_button_clicked_with_streaming(b):
    message = chat_input.value
    if not message.strip():
        return
    
    chat_input.value = ''
    
    with chat_output:
        display(HTML(format_message("user", message)))
        
        # Add to memory
        memory.add_message("user", message)
        
        # Get the selected model
        model_type = model_type_dropdown.value
        model_name = None
        if model_type == "google":
            model_name = google_model_dropdown.value
        elif model_type == "ollama":
            model_name = ollama_model_dropdown.value
        
        # Create a placeholder for the streaming response
        response_placeholder = widgets.HTML(
            value="<div id='streaming-response' style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;'><strong>🤖 Assistant</strong><div style='margin-top: 5px;'><span class='cursor'>▌</span></div></div>"
        )
        display(response_placeholder)
        
        # Stream the response
        full_response = ""
        async for chunk, error in stream_with_error_handling(
            message, model_type=model_type, model_name=model_name
        ):
            if error:
                response_placeholder.value = f"<div style='background-color: #ffe6e6; padding: 10px; border-radius: 5px; margin: 10px 0;'><strong>❌ Error</strong><div style='margin-top: 5px;'>{error}</div></div>"
                break
                
            full_response += chunk
            response_placeholder.value = f"<div id='streaming-response' style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;'><strong>🤖 Assistant</strong><div style='margin-top: 5px;'>{full_response}<span class='cursor'>▌</span></div></div>"
            
            # Small delay to make the streaming visible
            await asyncio.sleep(0.01)
        
        # Final response without cursor
        if not error:
            response_placeholder.value = f"<div style='background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;'><strong>🤖 Assistant</strong><div style='margin-top: 5px;'>{full_response}</div></div>"
            
            # Add to memory
            memory.add_message("assistant", full_response)
```

#### 1.3 API Streaming Endpoint
```python
@app.post("/api/chat/stream")
async def api_chat_stream(request: ChatRequest):
    """Stream chat responses."""
    try:
        # Get the selected model
        model_type = request.model_type or default_model_type
        model_name = request.model_name
        
        # Create a streaming response
        async def response_generator():
            async for chunk, error in stream_with_error_handling(
                request.message, model_type=model_type, model_name=model_name
            ):
                if error:
                    yield json.dumps({"error": error}) + "\n"
                    break
                    
                yield json.dumps({"chunk": chunk}) + "\n"
        
        return StreamingResponse(
            response_generator(),
            media_type="application/x-ndjson"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

## 2. FRP Integration Improvements

### Current Limitations
- Basic configuration only, no actual tunneling
- Limited error handling
- No status monitoring
- No custom domain validation

### Implementation Plan

#### 2.1 Robust FRP Setup
```python
class FRPManager:
    """Manage FRP tunneling with robust error handling and monitoring."""
    
    def __init__(self, base_dir):
        self.base_dir = Path(base_dir)
        self.frp_dir = self.base_dir / "frp"
        self.config_file = self.frp_dir / "frpc.ini"
        self.log_file = self.frp_dir / "frpc.log"
        self.process = None
        self.status = "not_started"
        self.last_error = None
        self.public_url = None
    
    async def setup(self, local_port, custom_domain=None, server_addr="frp.example.com", server_port=7000, token=None):
        """Set up FRP with error handling."""
        try:
            # Create FRP directory if it doesn't exist
            self.frp_dir.mkdir(parents=True, exist_ok=True)
            
            # Download FRP if not exists
            if not (self.frp_dir / "frpc").exists():
                print("⏳ Downloading FRP...")
                
                # Determine platform
                import platform
                system = platform.system().lower()
                machine = platform.machine().lower()
                
                if system == "linux":
                    if "arm" in machine or "aarch" in machine:
                        arch = "arm64" if "64" in machine else "arm"
                    else:
                        arch = "amd64" if "64" in machine else "386"
                    platform_str = f"linux_{arch}"
                elif system == "darwin":
                    arch = "arm64" if "arm" in machine else "amd64"
                    platform_str = f"darwin_{arch}"
                elif system == "windows":
                    arch = "amd64" if "64" in machine else "386"
                    platform_str = f"windows_{arch}"
                else:
                    raise ValueError(f"Unsupported platform: {system} {machine}")
                
                # Download and extract
                frp_version = "0.51.3"
                download_url = f"https://github.com/fatedier/frp/releases/download/v{frp_version}/frp_{frp_version}_{platform_str}.tar.gz"
                
                # Use aiohttp for async download
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    async with session.get(download_url) as response:
                        if response.status != 200:
                            raise ValueError(f"Failed to download FRP: HTTP {response.status}")
                        
                        # Save to file
                        tar_path = self.frp_dir / "frp.tar.gz"
                        with open(tar_path, "wb") as f:
                            f.write(await response.read())
                
                # Extract
                import tarfile
                with tarfile.open(tar_path, "r:gz") as tar:
                    # Extract only the files we need
                    for member in tar.getmembers():
                        if member.name.endswith(("frpc", "frpc.exe", "frpc.ini")):
                            # Rename to remove version and platform
                            member.name = os.path.basename(member.name)
                            tar.extract(member, self.frp_dir)
                
                # Make executable
                if system != "windows":
                    os.chmod(self.frp_dir / "frpc", 0o755)
                
                # Clean up
                os.remove(tar_path)
                print("✅ FRP downloaded and extracted")
            
            # Validate custom domain
            if custom_domain:
                import re
                if not re.match(r'^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$', custom_domain):
                    raise ValueError(f"Invalid domain name: {custom_domain}")
            else:
                # Generate a random subdomain
                import random
                import string
                random_id = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
                custom_domain = f"manus-{random_id}.example.com"
            
            # Create FRP config
            frp_config = f"""
[common]
server_addr = {server_addr}
server_port = {server_port}
{"token = " + token if token else ""}
log_file = {self.log_file}

[web]
type = http
local_port = {local_port}
custom_domains = {custom_domain}
"""
            
            with open(self.config_file, "w") as f:
                f.write(frp_config)
            
            self.public_url = f"http://{custom_domain}"
            return {
                "success": True,
                "message": "FRP configuration created",
                "config_path": str(self.config_file),
                "domain": custom_domain,
                "local_port": local_port,
                "url": self.public_url
            }
            
        except Exception as e:
            self.last_error = str(e)
            self.status = "error"
            return {
                "success": False,
                "error": str(e)
            }
    
    async def start(self):
        """Start the FRP tunnel."""
        if self.process and self.process.poll() is None:
            return {"success": False, "error": "FRP is already running"}
        
        try:
            # Determine the executable name
            import platform
            frpc_exe = "frpc.exe" if platform.system().lower() == "windows" else "frpc"
            frpc_path = self.frp_dir / frpc_exe
            
            # Start FRP
            self.process = subprocess.Popen(
                [str(frpc_path), "-c", str(self.config_file)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a moment for it to start
            await asyncio.sleep(2)
            
            # Check if it's running
            if self.process.poll() is not None:
                stdout, stderr = self.process.communicate()
                self.last_error = stderr
                self.status = "error"
                return {
                    "success": False,
                    "error": f"FRP failed to start: {stderr}"
                }
            
            self.status = "running"
            return {
                "success": True,
                "message": "FRP tunnel started",
                "url": self.public_url,
                "pid": self.process.pid
            }
            
        except Exception as e:
            self.last_error = str(e)
            self.status = "error"
            return {
                "success": False,
                "error": str(e)
            }
    
    async def stop(self):
        """Stop the FRP tunnel."""
        if not self.process:
            return {"success": False, "error": "FRP is not running"}
        
        try:
            # Terminate the process
            self.process.terminate()
            
            # Wait for it to terminate
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Force kill if it doesn't terminate
                self.process.kill()
            
            self.status = "stopped"
            return {
                "success": True,
                "message": "FRP tunnel stopped"
            }
            
        except Exception as e:
            self.last_error = str(e)
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_status(self):
        """Get the status of the FRP tunnel."""
        if not self.process:
            return {
                "status": "not_started",
                "url": None,
                "error": self.last_error
            }
        
        # Check if the process is still running
        if self.process.poll() is not None:
            self.status = "stopped"
        
        # Read the log file for errors
        log_errors = []
        if self.log_file.exists():
            with open(self.log_file, "r") as f:
                for line in f.readlines()[-10:]:  # Last 10 lines
                    if "error" in line.lower():
                        log_errors.append(line.strip())
        
        return {
            "status": self.status,
            "url": self.public_url,
            "pid": self.process.pid if self.process else None,
            "error": self.last_error,
            "log_errors": log_errors
        }
```

#### 2.2 FRP API Endpoints
```python
# Initialize FRP manager
frp_manager = FRPManager(BASE_DIR)

@app.post("/api/frp/setup")
async def api_frp_setup(
    local_port: int = 8000,
    custom_domain: Optional[str] = None,
    server_addr: str = "frp.example.com",
    server_port: int = 7000,
    token: Optional[str] = None
):
    """Set up FRP configuration."""
    result = await frp_manager.setup(
        local_port=local_port,
        custom_domain=custom_domain,
        server_addr=server_addr,
        server_port=server_port,
        token=token
    )
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.post("/api/frp/start")
async def api_frp_start():
    """Start the FRP tunnel."""
    result = await frp_manager.start()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.post("/api/frp/stop")
async def api_frp_stop():
    """Stop the FRP tunnel."""
    result = await frp_manager.stop()
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return result

@app.get("/api/frp/status")
async def api_frp_status():
    """Get the status of the FRP tunnel."""
    return await frp_manager.get_status()
```

## 3. Enhanced GUI Features

### Current Limitations
- Limited interactivity in the UI
- No real-time updates
- Basic styling and layout
- Limited visualization capabilities

### Implementation Plan

#### 3.1 Interactive Code Editor
```python
def create_enhanced_code_editor():
    """Create an enhanced code editor with syntax highlighting and more features."""
    # Code editor with line numbers and syntax highlighting
    code_editor_html = widgets.HTML(
        value="""
        <div id="editor-container" style="width: 100%; height: 300px; border: 1px solid #ddd; border-radius: 4px;">
            <div id="editor" style="width: 100%; height: 100%;"></div>
        </div>
        <script src="https://cdnjs.cloudflare.com/ajax/libs/ace/1.4.12/ace.js"></script>
        <script>
            var editor = ace.edit("editor");
            editor.setTheme("ace/theme/monokai");
            editor.session.setMode("ace/mode/python");
            editor.setValue("# Enter your Python code here\\nprint(\\"Hello, world!\\")");
            editor.clearSelection();
            
            // Function to get code from editor
            window.getEditorCode = function() {
                return editor.getValue();
            }
            
            // Function to set code in editor
            window.setEditorCode = function(code) {
                editor.setValue(code);
                editor.clearSelection();
            }
        </script>
        """
    )
    
    # Function to get code from editor
    def get_code():
        from IPython.display import Javascript
        return Javascript("IPython.notebook.kernel.execute('code = \"' + window.getEditorCode().replace(/\\n/g, '\\\\n').replace(/\"/g, '\\\\\"') + '\"')")
    
    # Function to set code in editor
    def set_code(code):
        from IPython.display import Javascript
        return Javascript(f"window.setEditorCode(`{code}`)")
    
    # Buttons
    run_button = widgets.Button(
        description="Run",
        button_style="success",
        icon="play"
    )
    
    format_button = widgets.Button(
        description="Format",
        button_style="info",
        icon="indent"
    )
    
    save_button = widgets.Button(
        description="Save",
        button_style="primary",
        icon="save"
    )
    
    load_button = widgets.Button(
        description="Load",
        button_style="warning",
        icon="folder-open"
    )
    
    # File name input
    file_name = widgets.Text(
        value="script.py",
        placeholder="Enter file name",
        description="File:",
        style={"description_width": "initial"}
    )
    
    # Output area
    output = widgets.Output()
    
    # Button handlers
    def on_run_button_clicked(b):
        with output:
            clear_output()
            display(get_code())
            # Get the code and execute it
            # This would be implemented with the actual code execution
    
    def on_format_button_clicked(b):
        with output:
            clear_output()
            # Format the code using black or autopep8
            # This would be implemented with the actual formatting
    
    def on_save_button_clicked(b):
        with output:
            clear_output()
            # Save the code to a file
            # This would be implemented with the actual file saving
    
    def on_load_button_clicked(b):
        with output:
            clear_output()
            # Load code from a file
            # This would be implemented with the actual file loading
    
    # Connect handlers
    run_button.on_click(on_run_button_clicked)
    format_button.on_click(on_format_button_clicked)
    save_button.on_click(on_save_button_clicked)
    load_button.on_click(on_load_button_clicked)
    
    # Layout
    file_controls = widgets.HBox([file_name, save_button, load_button])
    code_controls = widgets.HBox([run_button, format_button])
    
    return widgets.VBox([
        code_editor_html,
        file_controls,
        code_controls,
        output
    ])
```

#### 3.2 Real-time Chat Updates
```python
def create_enhanced_chat_interface():
    """Create an enhanced chat interface with real-time updates."""
    # Chat history container
    chat_container = widgets.HTML(
        value="""
        <div id="chat-container" style="height: 400px; overflow-y: auto; border: 1px solid #ddd; border-radius: 4px; padding: 10px; background-color: #f9f9f9;">
            <div id="chat-messages"></div>
        </div>
        <script>
            // Function to add a message to the chat
            window.addChatMessage = function(role, content, timestamp) {
                var container = document.getElementById('chat-messages');
                var msgDiv = document.createElement('div');
                
                // Style based on role
                var bgColor = role === 'user' ? '#e6f7ff' : '#f0f0f0';
                var icon = role === 'user' ? '👤' : '🤖';
                
                msgDiv.style.backgroundColor = bgColor;
                msgDiv.style.padding = '10px';
                msgDiv.style.borderRadius = '5px';
                msgDiv.style.marginBottom = '10px';
                
                // Format timestamp
                var time = timestamp ? new Date(timestamp).toLocaleTimeString() : new Date().toLocaleTimeString();
                
                // Set content
                msgDiv.innerHTML = `
                    <div style="display: flex; justify-content: space-between;">
                        <strong>${icon} ${role.charAt(0).toUpperCase() + role.slice(1)}</strong>
                        <span style="color: #666; font-size: 0.8em;">${time}</span>
                    </div>
                    <div style="margin-top: 5px;">${content}</div>
                `;
                
                // Add to container and scroll to bottom
                container.appendChild(msgDiv);
                container.scrollTop = container.scrollHeight;
            }
            
            // Function to clear the chat
            window.clearChat = function() {
                document.getElementById('chat-messages').innerHTML = '';
            }
            
            // Function to add a typing indicator
            window.showTyping = function(show) {
                var container = document.getElementById('chat-messages');
                var typingDiv = document.getElementById('typing-indicator');
                
                if (show) {
                    if (!typingDiv) {
                        typingDiv = document.createElement('div');
                        typingDiv.id = 'typing-indicator';
                        typingDiv.style.backgroundColor = '#f0f0f0';
                        typingDiv.style.padding = '10px';
                        typingDiv.style.borderRadius = '5px';
                        typingDiv.style.marginBottom = '10px';
                        typingDiv.innerHTML = `
                            <div style="display: flex; align-items: center;">
                                <strong>🤖 Assistant</strong>
                                <div style="margin-left: 10px; display: flex;">
                                    <div class="dot" style="background-color: #333; width: 5px; height: 5px; border-radius: 50%; margin: 0 2px; animation: typing 1s infinite;"></div>
                                    <div class="dot" style="background-color: #333; width: 5px; height: 5px; border-radius: 50%; margin: 0 2px; animation: typing 1s infinite 0.2s;"></div>
                                    <div class="dot" style="background-color: #333; width: 5px; height: 5px; border-radius: 50%; margin: 0 2px; animation: typing 1s infinite 0.4s;"></div>
                                </div>
                            </div>
                        `;
                        container.appendChild(typingDiv);
                        container.scrollTop = container.scrollHeight;
                    }
                } else {
                    if (typingDiv) {
                        typingDiv.remove();
                    }
                }
            }
            
            // Add typing animation
            var style = document.createElement('style');
            style.innerHTML = `
                @keyframes typing {
                    0% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                    100% { transform: translateY(0); }
                }
            `;
            document.head.appendChild(style);
        </script>
        """
    )
    
    # Chat input
    chat_input = widgets.Text(
        value='',
        placeholder='Type a message...',
        description='',
        disabled=False,
        layout=widgets.Layout(width='80%')
    )
    
    # Send button
    send_button = widgets.Button(
        description='Send',
        disabled=False,
        button_style='primary',
        tooltip='Send message',
        icon='paper-plane',
        layout=widgets.Layout(width='19%')
    )
    
    # Clear button
    clear_button = widgets.Button(
        description='Clear',
        disabled=False,
        button_style='danger',
        tooltip='Clear chat history',
        icon='trash'
    )
    
    # Output for JavaScript execution
    js_output = widgets.Output()
    
    # Function to add a message to the chat
    def add_chat_message(role, content, timestamp=None):
        from IPython.display import Javascript
        timestamp_str = f"'{timestamp}'" if timestamp else "null"
        return Javascript(f"window.addChatMessage('{role}', `{content.replace('`', '\\`')}`, {timestamp_str})")
    
    # Function to clear the chat
    def clear_chat():
        from IPython.display import Javascript
        return Javascript("window.clearChat()")
    
    # Function to show typing indicator
    def show_typing(show):
        from IPython.display import Javascript
        return Javascript(f"window.showTyping({str(show).lower()})")
    
    # Button handlers
    async def on_send_button_clicked(b):
        message = chat_input.value
        if not message.strip():
            return
        
        chat_input.value = ''
        
        # Display user message
        with js_output:
            display(add_chat_message('user', message))
        
        # Add to memory
        memory.add_message("user", message)
        
        # Show typing indicator
        with js_output:
            display(show_typing(True))
        
        # Get the selected model
        model_type = model_type_dropdown.value
        model_name = None
        if model_type == "google":
            model_name = google_model_dropdown.value
        elif model_type == "ollama":
            model_name = ollama_model_dropdown.value
        
        # Generate response
        try:
            response, confidence = await chat(message, model_name=model_name, model_type=model_type)
            
            # Hide typing indicator
            with js_output:
                display(show_typing(False))
            
            # Display assistant message
            with js_output:
                display(add_chat_message('assistant', response))
            
            # Add to memory
            memory.add_message("assistant", response)
            
        except Exception as e:
            # Hide typing indicator
            with js_output:
                display(show_typing(False))
            
            # Display error
            with js_output:
                display(add_chat_message('system', f"Error: {str(e)}"))
    
    def on_clear_button_clicked(b):
        # Clear memory
        memory.clear_conversation()
        
        # Clear chat display
        with js_output:
            display(clear_chat())
    
    # Connect handlers
    send_button.on_click(lambda b: asyncio.create_task(on_send_button_clicked(b)))
    chat_input.on_submit(lambda _: asyncio.create_task(on_send_button_clicked(None)))
    clear_button.on_click(on_clear_button_clicked)
    
    # Layout
    input_area = widgets.HBox([chat_input, send_button])
    
    return widgets.VBox([
        chat_container,
        input_area,
        clear_button,
        js_output
    ])
```

#### 3.3 Interactive Dashboard
```python
def create_dashboard():
    """Create an interactive dashboard with system status and metrics."""
    # System status
    status_html = widgets.HTML(
        value="""
        <div style="padding: 15px; background-color: #f5f5f5; border-radius: 5px; margin-bottom: 15px;">
            <h3 style="margin-top: 0;">System Status</h3>
            <div id="system-status">
                <div class="status-item">
                    <span class="status-label">Model System:</span>
                    <span class="status-value" id="model-status">Loading...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Tool Registry:</span>
                    <span class="status-value" id="tool-status">Loading...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Web Server:</span>
                    <span class="status-value" id="server-status">Loading...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">FRP Tunnel:</span>
                    <span class="status-value" id="frp-status">Loading...</span>
                </div>
                <div class="status-item">
                    <span class="status-label">Human Review:</span>
                    <span class="status-value" id="review-status">Loading...</span>
                </div>
            </div>
        </div>
        
        <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
            <div style="width: 48%; padding: 15px; background-color: #e6f7ff; border-radius: 5px;">
                <h3 style="margin-top: 0;">Model Usage</h3>
                <div id="model-usage">
                    <canvas id="model-chart" width="400" height="200"></canvas>
                </div>
            </div>
            
            <div style="width: 48%; padding: 15px; background-color: #e6ffe6; border-radius: 5px;">
                <h3 style="margin-top: 0;">Tool Usage</h3>
                <div id="tool-usage">
                    <canvas id="tool-chart" width="400" height="200"></canvas>
                </div>
            </div>
        </div>
        
        <div style="padding: 15px; background-color: #fff3cd; border-radius: 5px;">
            <h3 style="margin-top: 0;">Recent Activity</h3>
            <div id="recent-activity">
                <table style="width: 100%; border-collapse: collapse;">
                    <thead>
                        <tr>
                            <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Time</th>
                            <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Type</th>
                            <th style="text-align: left; padding: 8px; border-bottom: 1px solid #ddd;">Details</th>
                        </tr>
                    </thead>
                    <tbody id="activity-log">
                        <tr>
                            <td colspan="3" style="text-align: center; padding: 8px;">Loading...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <script>
            // Initialize charts
            var modelCtx = document.getElementById('model-chart').getContext('2d');
            var modelChart = new Chart(modelCtx, {
                type: 'bar',
                data: {
                    labels: ['Google', 'Ollama', 'Fallback'],
                    datasets: [{
                        label: 'Requests',
                        data: [0, 0, 0],
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)',
                            'rgba(255, 99, 132, 0.5)'
                        ],
                        borderColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(255, 99, 132, 1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            });
            
            var toolCtx = document.getElementById('tool-chart').getContext('2d');
            var toolChart = new Chart(toolCtx, {
                type: 'doughnut',
                data: {
                    labels: ['File System', 'Code', 'Research', 'Deployment', 'Agent'],
                    datasets: [{
                        label: 'Usage',
                        data: [0, 0, 0, 0, 0],
                        backgroundColor: [
                            'rgba(54, 162, 235, 0.5)',
                            'rgba(255, 206, 86, 0.5)',
                            'rgba(75, 192, 192, 0.5)',
                            'rgba(153, 102, 255, 0.5)',
                            'rgba(255, 159, 64, 0.5)'
                        ],
                        borderColor: [
                            'rgba(54, 162, 235, 1)',
                            'rgba(255, 206, 86, 1)',
                            'rgba(75, 192, 192, 1)',
                            'rgba(153, 102, 255, 1)',
                            'rgba(255, 159, 64, 1)'
                        ],
                        borderWidth: 1
                    }]
                }
            });
            
            // Function to update system status
            window.updateSystemStatus = function(status) {
                document.getElementById('model-status').innerHTML = status.model_system;
                document.getElementById('tool-status').innerHTML = status.tool_registry;
                document.getElementById('server-status').innerHTML = status.web_server;
                document.getElementById('frp-status').innerHTML = status.frp_tunnel;
                document.getElementById('review-status').innerHTML = status.human_review;
            }
            
            // Function to update model usage chart
            window.updateModelChart = function(data) {
                modelChart.data.datasets[0].data = [
                    data.google || 0,
                    data.ollama || 0,
                    data.fallback || 0
                ];
                modelChart.update();
            }
            
            // Function to update tool usage chart
            window.updateToolChart = function(data) {
                toolChart.data.datasets[0].data = [
                    data.file_system || 0,
                    data.code || 0,
                    data.research || 0,
                    data.deployment || 0,
                    data.agent || 0
                ];
                toolChart.update();
            }
            
            // Function to update activity log
            window.updateActivityLog = function(activities) {
                var tbody = document.getElementById('activity-log');
                tbody.innerHTML = '';
                
                activities.forEach(function(activity) {
                    var row = document.createElement('tr');
                    
                    var timeCell = document.createElement('td');
                    timeCell.style.padding = '8px';
                    timeCell.style.borderBottom = '1px solid #ddd';
                    timeCell.textContent = activity.time;
                    
                    var typeCell = document.createElement('td');
                    typeCell.style.padding = '8px';
                    typeCell.style.borderBottom = '1px solid #ddd';
                    typeCell.textContent = activity.type;
                    
                    var detailsCell = document.createElement('td');
                    detailsCell.style.padding = '8px';
                    detailsCell.style.borderBottom = '1px solid #ddd';
                    detailsCell.textContent = activity.details;
                    
                    row.appendChild(timeCell);
                    row.appendChild(typeCell);
                    row.appendChild(detailsCell);
                    
                    tbody.appendChild(row);
                });
            }
        </script>
        """
    )
    
    # Refresh button
    refresh_button = widgets.Button(
        description='Refresh Dashboard',
        disabled=False,
        button_style='info',
        tooltip='Refresh dashboard data',
        icon='sync'
    )
    
    # Output for JavaScript execution
    js_output = widgets.Output()
    
    # Function to update system status
    def update_system_status():
        from IPython.display import Javascript
        
        # Get actual status (this would be implemented with real status checks)
        status = {
            "model_system": f"<span style='color: green;'>✓ Active</span> ({default_model_type.capitalize()})",
            "tool_registry": f"<span style='color: green;'>✓ Active</span> ({len(TOOL_REGISTRY)} tools)",
            "web_server": "<span style='color: green;'>✓ Running</span> (Port 8000)",
            "frp_tunnel": "<span style='color: orange;'>⚠ Configured</span> (Not running)",
            "human_review": f"<span style='color: {'green' if config.get('human_review_enabled', True) else 'red'}'>{'✓ Enabled' if config.get('human_review_enabled', True) else '✗ Disabled'}</span>"
        }
        
        return Javascript(f"window.updateSystemStatus({json.dumps(status)})")
    
    # Function to update model usage chart
    def update_model_chart():
        from IPython.display import Javascript
        
        # Get actual usage data (this would be implemented with real usage tracking)
        data = {
            "google": 15,
            "ollama": 8,
            "fallback": 2
        }
        
        return Javascript(f"window.updateModelChart({json.dumps(data)})")
    
    # Function to update tool usage chart
    def update_tool_chart():
        from IPython.display import Javascript
        
        # Get actual usage data (this would be implemented with real usage tracking)
        data = {
            "file_system": 12,
            "code": 20,
            "research": 8,
            "deployment": 5,
            "agent": 15
        }
        
        return Javascript(f"window.updateToolChart({json.dumps(data)})")
    
    # Function to update activity log
    def update_activity_log():
        from IPython.display import Javascript
        
        # Get actual activity data (this would be implemented with real activity tracking)
        activities = [
            {"time": "10:15 AM", "type": "Chat", "details": "User asked about Python functions"},
            {"time": "10:18 AM", "type": "Tool", "details": "Executed execute_python tool"},
            {"time": "10:20 AM", "type": "Code", "details": "Generated code for Fibonacci sequence"},
            {"time": "10:25 AM", "type": "Review", "details": "Human approved response"},
            {"time": "10:30 AM", "type": "Deploy", "details": "Launched website at /site/my_site"}
        ]
        
        return Javascript(f"window.updateActivityLog({json.dumps(activities)})")
    
    # Function to refresh all dashboard data
    def refresh_dashboard(b=None):
        with js_output:
            display(update_system_status())
            display(update_model_chart())
            display(update_tool_chart())
            display(update_activity_log())
    
    # Connect handler
    refresh_button.on_click(refresh_dashboard)
    
    # Initial refresh
    refresh_dashboard()
    
    return widgets.VBox([
        status_html,
        refresh_button,
        js_output
    ])
```

## 4. Implementation Timeline

### Phase 1: Streaming Response Enhancements (1-2 days)
- Implement robust streaming core
- Add UI streaming improvements
- Create API streaming endpoint
- Test with various models and scenarios

### Phase 2: FRP Integration Improvements (2-3 days)
- Implement FRP Manager class
- Add API endpoints for FRP control
- Create UI for FRP management
- Test with actual FRP servers

### Phase 3: Enhanced GUI Features (3-4 days)
- Implement interactive code editor
- Create real-time chat updates
- Develop interactive dashboard
- Integrate all UI components

### Phase 4: Testing and Refinement (2-3 days)
- Comprehensive testing of all features
- Performance optimization
- Bug fixes and refinements
- Documentation updates

## 5. Conclusion

These advanced features will significantly enhance the Google Manus System, making it more robust, interactive, and user-friendly. The streaming response improvements will provide a more natural chat experience, the FRP integration enhancements will enable reliable web deployment, and the enhanced GUI features will make the system more intuitive and powerful.

By implementing these features, the Google Manus System will become a comprehensive platform for AI-assisted coding, research, and web deployment, with a focus on user experience and reliability.