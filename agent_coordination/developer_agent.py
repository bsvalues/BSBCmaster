"""
Developer Agent for Benton County Assessor's Office AI Platform

This module implements a specialized AI agent that can contribute
to building and improving the application codebase.
"""

import os
import re
import json
import uuid
import logging
import inspect
import importlib
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime

from core.message import Message, CommandMessage, ResponseMessage, ErrorMessage
from mcp.agent import Agent
from core.hub_enhanced import CoreHubEnhanced


class DeveloperAgent(Agent):
    """
    AI agent specialized in software development tasks.
    
    This agent can contribute to building and improving the application by:
    - Generating new code components based on requirements
    - Reviewing and refactoring existing code
    - Creating and improving tests
    - Writing and updating documentation
    """
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        """
        Initialize the Developer Agent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration
        """
        super().__init__(agent_id, config)
        
        self.logger = logging.getLogger(f"developer_agent.{agent_id}")
        self.specialization = config.get("specialization", "full_stack")
        self.code_generation_mode = config.get("code_generation_mode", "incremental")
        
        # Register message handlers
        self.register_handler("execute_development_task", self._handle_development_task)
        self.register_handler("review_code", self._handle_code_review)
        self.register_handler("generate_documentation", self._handle_documentation)
        
        self.logger.info(f"Developer Agent {agent_id} initialized with specialization {self.specialization}")
    
    def _handle_development_task(self, message: Message) -> None:
        """
        Handle a development task command.
        
        Args:
            message: Development task command message
        """
        if not isinstance(message, CommandMessage):
            return
        
        params = message.payload.get("parameters", {})
        task_id = params.get("task_id")
        task_type = params.get("task_type")
        title = params.get("title")
        description = params.get("description")
        related_files = params.get("related_files", [])
        
        if not task_id or not task_type:
            self._send_error_response(
                message,
                "INVALID_PARAMETERS",
                "Task ID and task type are required"
            )
            return
        
        self.logger.info(f"Received development task: {task_id} ({task_type})")
        
        # Send acknowledgment
        self._send_task_update(
            task_id=task_id,
            status="in_progress",
            message_id=message.message_id,
            correlation_id=message.correlation_id,
            source_agent_id=message.source_agent_id
        )
        
        # Execute task based on type
        result = None
        
        try:
            if task_type == "code_generation":
                result = self._execute_code_generation(task_id, title, description, related_files)
            elif task_type == "code_review":
                result = self._execute_code_review(task_id, title, description, related_files)
            elif task_type == "testing":
                result = self._execute_testing_task(task_id, title, description, related_files)
            elif task_type == "documentation":
                result = self._execute_documentation_task(task_id, title, description, related_files)
            elif task_type == "code_improvement":
                result = self._execute_code_improvement(task_id, title, description, related_files)
            else:
                self._send_error_response(
                    message,
                    "UNSUPPORTED_TASK_TYPE",
                    f"Task type {task_type} is not supported"
                )
                return
                
            # Send completion update
            self._send_task_update(
                task_id=task_id,
                status="completed",
                result=result,
                message_id=message.message_id,
                correlation_id=message.correlation_id,
                source_agent_id=message.source_agent_id
            )
            
            self.logger.info(f"Completed development task: {task_id}")
            
        except Exception as e:
            self.logger.error(f"Error executing task {task_id}: {str(e)}")
            
            # Send failure update
            self._send_task_update(
                task_id=task_id,
                status="failed",
                result={"error": str(e)},
                message_id=message.message_id,
                correlation_id=message.correlation_id,
                source_agent_id=message.source_agent_id
            )
    
    def _handle_code_review(self, message: Message) -> None:
        """
        Handle a code review command.
        
        Args:
            message: Code review command message
        """
        if not isinstance(message, CommandMessage):
            return
        
        params = message.payload.get("parameters", {})
        file_path = params.get("file_path")
        review_type = params.get("review_type", "general")
        
        if not file_path:
            self._send_error_response(
                message,
                "INVALID_PARAMETERS",
                "File path is required"
            )
            return
        
        self.logger.info(f"Received code review request for {file_path}")
        
        try:
            # Read the file
            if not os.path.exists(file_path):
                self._send_error_response(
                    message,
                    "FILE_NOT_FOUND",
                    f"File {file_path} not found"
                )
                return
            
            with open(file_path, "r") as f:
                code = f.read()
            
            # Perform code review
            review = self._review_code(file_path, code, review_type)
            
            # Send response
            response = ResponseMessage(
                source_agent_id=self.agent_id,
                target_agent_id=message.source_agent_id,
                status="success",
                result=review,
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error reviewing code: {str(e)}")
            self._send_error_response(
                message,
                "REVIEW_ERROR",
                f"Error reviewing code: {str(e)}"
            )
    
    def _handle_documentation(self, message: Message) -> None:
        """
        Handle a documentation generation command.
        
        Args:
            message: Documentation generation command message
        """
        if not isinstance(message, CommandMessage):
            return
        
        params = message.payload.get("parameters", {})
        subject = params.get("subject")
        doc_type = params.get("doc_type", "function")
        
        if not subject:
            self._send_error_response(
                message,
                "INVALID_PARAMETERS",
                "Subject is required"
            )
            return
        
        self.logger.info(f"Received documentation request for {subject}")
        
        try:
            # Generate documentation
            documentation = self._generate_documentation(subject, doc_type)
            
            # Send response
            response = ResponseMessage(
                source_agent_id=self.agent_id,
                target_agent_id=message.source_agent_id,
                status="success",
                result=documentation,
                original_message_id=message.message_id,
                correlation_id=message.correlation_id
            )
            self.send_message(response)
            
        except Exception as e:
            self.logger.error(f"Error generating documentation: {str(e)}")
            self._send_error_response(
                message,
                "DOCUMENTATION_ERROR",
                f"Error generating documentation: {str(e)}"
            )
    
    def _execute_code_generation(
        self, 
        task_id: str, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a code generation task.
        
        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Task result
        """
        self.logger.info(f"Executing code generation task: {task_id}")
        
        # Analyze requirements
        requirements = self._extract_requirements(description)
        
        # Gather context from related files
        context = self._gather_context(related_files)
        
        # Determine output file
        output_file = self._determine_output_file(title, description, related_files)
        
        # Generate code
        code = self._generate_code(requirements, context, output_file)
        
        # Write code to file
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, "w") as f:
            f.write(code)
        
        # Submit code contribution
        self._submit_code_contribution(task_id, output_file, code)
        
        return {
            "file_path": output_file,
            "code_size": len(code),
            "requirements_implemented": requirements
        }
    
    def _execute_code_review(
        self, 
        task_id: str, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a code review task.
        
        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Task result
        """
        self.logger.info(f"Executing code review task: {task_id}")
        
        reviews = []
        
        for file_path in related_files:
            if not os.path.exists(file_path):
                self.logger.warning(f"File {file_path} not found, skipping review")
                continue
                
            with open(file_path, "r") as f:
                code = f.read()
                
            review = self._review_code(file_path, code, "comprehensive")
            reviews.append({
                "file_path": file_path,
                "review": review
            })
        
        return {
            "reviews": reviews,
            "file_count": len(reviews)
        }
    
    def _execute_testing_task(
        self, 
        task_id: str, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a testing task.
        
        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Task result
        """
        self.logger.info(f"Executing testing task: {task_id}")
        
        test_files = []
        
        for file_path in related_files:
            if not os.path.exists(file_path):
                self.logger.warning(f"File {file_path} not found, skipping test generation")
                continue
                
            # Determine test file path
            test_file = self._determine_test_file(file_path)
            
            # Generate test code
            with open(file_path, "r") as f:
                code = f.read()
                
            test_code = self._generate_test_code(file_path, code)
            
            # Write test code to file
            os.makedirs(os.path.dirname(test_file), exist_ok=True)
            with open(test_file, "w") as f:
                f.write(test_code)
                
            test_files.append({
                "source_file": file_path,
                "test_file": test_file,
                "test_size": len(test_code)
            })
            
            # Submit code contribution
            self._submit_code_contribution(task_id, test_file, test_code)
        
        return {
            "test_files": test_files,
            "file_count": len(test_files)
        }
    
    def _execute_documentation_task(
        self, 
        task_id: str, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a documentation task.
        
        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Task result
        """
        self.logger.info(f"Executing documentation task: {task_id}")
        
        doc_files = []
        
        if "README" in title or "readme" in title.lower():
            # Generate README
            readme_path = os.path.join(os.path.dirname(related_files[0]) if related_files else ".", "README.md")
            readme_content = self._generate_readme(description, related_files)
            
            with open(readme_path, "w") as f:
                f.write(readme_content)
                
            doc_files.append({
                "file_path": readme_path,
                "content_size": len(readme_content),
                "type": "readme"
            })
            
            # Submit code contribution
            self._submit_code_contribution(task_id, readme_path, readme_content)
            
        else:
            # Generate docstrings or other documentation
            for file_path in related_files:
                if not os.path.exists(file_path):
                    self.logger.warning(f"File {file_path} not found, skipping documentation")
                    continue
                    
                with open(file_path, "r") as f:
                    original_code = f.read()
                    
                # Add or improve docstrings
                improved_code = self._improve_docstrings(file_path, original_code)
                
                if improved_code != original_code:
                    with open(file_path, "w") as f:
                        f.write(improved_code)
                        
                    doc_files.append({
                        "file_path": file_path,
                        "content_size": len(improved_code),
                        "type": "docstrings"
                    })
                    
                    # Submit code contribution
                    self._submit_code_contribution(task_id, file_path, improved_code)
        
        return {
            "doc_files": doc_files,
            "file_count": len(doc_files)
        }
    
    def _execute_code_improvement(
        self, 
        task_id: str, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> Dict[str, Any]:
        """
        Execute a code improvement task.
        
        Args:
            task_id: Task ID
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Task result
        """
        self.logger.info(f"Executing code improvement task: {task_id}")
        
        improved_files = []
        
        for file_path in related_files:
            if not os.path.exists(file_path):
                self.logger.warning(f"File {file_path} not found, skipping improvement")
                continue
                
            with open(file_path, "r") as f:
                original_code = f.read()
                
            # Improve code
            improved_code = self._improve_code(file_path, original_code, description)
            
            if improved_code != original_code:
                with open(file_path, "w") as f:
                    f.write(improved_code)
                    
                improved_files.append({
                    "file_path": file_path,
                    "original_size": len(original_code),
                    "improved_size": len(improved_code)
                })
                
                # Submit code contribution
                self._submit_code_contribution(task_id, file_path, improved_code)
        
        return {
            "improved_files": improved_files,
            "file_count": len(improved_files)
        }
    
    def _extract_requirements(self, description: str) -> List[str]:
        """
        Extract requirements from task description.
        
        Args:
            description: Task description
            
        Returns:
            List of requirements
        """
        # Simple extraction based on bullet points or numbered lists
        requirements = []
        
        # Extract bullet points
        bullet_pattern = r"[\*\-\•]\s*(.*?)(?=\n[\*\-\•]|\n\n|$)"
        bullets = re.findall(bullet_pattern, description, re.DOTALL)
        requirements.extend([b.strip() for b in bullets])
        
        # Extract numbered list items
        numbered_pattern = r"\d+\.\s*(.*?)(?=\n\d+\.|\n\n|$)"
        numbered = re.findall(numbered_pattern, description, re.DOTALL)
        requirements.extend([n.strip() for n in numbered])
        
        # If no structured requirements found, split by newlines
        if not requirements:
            requirements = [line.strip() for line in description.split("\n") if line.strip()]
        
        return requirements
    
    def _gather_context(self, related_files: List[str]) -> Dict[str, Any]:
        """
        Gather context from related files.
        
        Args:
            related_files: List of related files
            
        Returns:
            Context information
        """
        context = {
            "files": {},
            "dependencies": [],
            "imports": []
        }
        
        for file_path in related_files:
            if not os.path.exists(file_path):
                continue
                
            with open(file_path, "r") as f:
                content = f.read()
                
            context["files"][file_path] = content
            
            # Extract imports
            if file_path.endswith(".py"):
                import_pattern = r"^\s*(?:from|import)\s+([a-zA-Z0-9_\.]+)"
                imports = re.findall(import_pattern, content, re.MULTILINE)
                context["imports"].extend(imports)
                
            elif file_path.endswith(".js"):
                import_pattern = r"(?:import|require)\s*\(\s*['\"]([^'\"]+)['\"]"
                imports = re.findall(import_pattern, content)
                context["imports"].extend(imports)
        
        # Remove duplicates
        context["imports"] = list(set(context["imports"]))
        
        return context
    
    def _determine_output_file(
        self, 
        title: str, 
        description: str, 
        related_files: List[str]
    ) -> str:
        """
        Determine the output file for code generation.
        
        Args:
            title: Task title
            description: Task description
            related_files: Related files
            
        Returns:
            Output file path
        """
        # Extract file path hints from description
        file_hint_pattern = r"(?:create|implement|generate)[^'\"]*['\"]([^'\"]+)['\"]"
        file_hints = re.findall(file_hint_pattern, description, re.IGNORECASE)
        
        if file_hints:
            return file_hints[0]
            
        # Infer from title
        words = re.findall(r"\w+", title.lower())
        
        if "agent" in words:
            directory = "agent_coordination"
            filename = "_".join([w for w in words if w not in ["implement", "create", "add", "new", "agent"]])
            if not filename:
                filename = "specialized_agent"
            return f"{directory}/{filename}.py"
            
        elif "core" in words:
            directory = "core"
            filename = "_".join([w for w in words if w not in ["implement", "create", "add", "new", "core"]])
            if not filename:
                filename = "component"
            return f"{directory}/{filename}.py"
            
        elif "api" in words or "endpoint" in words:
            directory = "app/api"
            filename = "_".join([w for w in words if w not in ["implement", "create", "add", "new", "api", "endpoint"]])
            if not filename:
                filename = "endpoints"
            return f"{directory}/{filename}.py"
            
        # Default: Use parent directory of first related file
        if related_files:
            directory = os.path.dirname(related_files[0])
            filename = os.path.basename(title.lower().replace(" ", "_"))
            return f"{directory}/{filename}.py"
            
        # Fallback
        return "component.py"
    
    def _determine_test_file(self, file_path: str) -> str:
        """
        Determine the test file path for a source file.
        
        Args:
            file_path: Source file path
            
        Returns:
            Test file path
        """
        directory = os.path.dirname(file_path)
        filename = os.path.basename(file_path)
        name, ext = os.path.splitext(filename)
        
        # Check if we're already in a test directory
        if "test" in directory.lower():
            return os.path.join(directory, f"test_{filename}")
            
        # Create test file in tests directory
        test_dir = os.path.join(directory, "tests")
        return os.path.join(test_dir, f"test_{filename}")
    
    def _generate_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """
        Generate code based on requirements and context.
        
        Args:
            requirements: List of requirements
            context: Context information
            output_file: Output file path
            
        Returns:
            Generated code
        """
        # This is a placeholder - in a real system, this would use
        # a more sophisticated code generation approach, possibly
        # integrating with an LLM or other AI models
        
        ext = os.path.splitext(output_file)[1].lower()
        
        if ext == ".py":
            return self._generate_python_code(requirements, context, output_file)
        elif ext == ".js":
            return self._generate_javascript_code(requirements, context, output_file)
        elif ext == ".html":
            return self._generate_html_code(requirements, context, output_file)
        elif ext == ".css":
            return self._generate_css_code(requirements, context, output_file)
        else:
            return self._generate_generic_code(requirements, context, output_file)
    
    def _generate_python_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """
        Generate Python code.
        
        Args:
            requirements: List of requirements
            context: Context information
            output_file: Output file path
            
        Returns:
            Generated code
        """
        # Extract module name from output file
        module_name = os.path.basename(output_file).replace(".py", "")
        module_name_title = module_name.replace("_", " ").title().replace(" ", "")
        
        # Build imports section
        imports = [
            "import os",
            "import json",
            "import logging",
            "from typing import Dict, Any, List, Optional"
        ]
        
        # Add related imports based on context
        if "core.message" in context["imports"] or any("message" in f for f in context["files"]):
            imports.append("from core.message import Message, CommandMessage, ResponseMessage, ErrorMessage")
            
        if "mcp.agent" in context["imports"] or any("agent" in f for f in context["files"]):
            imports.append("from mcp.agent import Agent")
            
        # Build class definition
        class_def = [
            f"class {module_name_title}:",
            f'    """',
            f"    {module_name_title} for Benton County Assessor's Office AI Platform",
            f"    ",
            f"    This component implements functionality to handle {module_name} operations.",
            f'    """',
            f"    ",
            f"    def __init__(self, config: Dict[str, Any]):",
            f'        """',
            f"        Initialize the {module_name_title}.",
            f"        ",
            f"        Args:",
            f"            config: Configuration options",
            f'        """',
            f"        self.config = config",
            f"        self.logger = logging.getLogger('{module_name}')"
        ]
        
        # Add methods based on requirements
        methods = []
        for req in requirements:
            method_name = self._extract_method_name(req)
            if method_name:
                methods.append(self._generate_method(method_name, req))
                
        # If no methods extracted, add a generic one
        if not methods:
            methods.append(self._generate_method("process", "Process data according to configuration"))
            
        # Combine everything
        code = "\n".join([
            '"""',
            f"{module_name_title} for Benton County Assessor's Office AI Platform",
            "",
            f"This module implements functionality to handle {module_name} operations.",
            '"""',
            "",
            "\n".join(imports),
            "",
            "",
            "\n".join(class_def),
            "",
            "\n".join(methods)
        ])
        
        return code
    
    def _generate_javascript_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """
        Generate JavaScript code.
        
        Args:
            requirements: List of requirements
            context: Context information
            output_file: Output file path
            
        Returns:
            Generated code
        """
        # Extract module name from output file
        module_name = os.path.basename(output_file).replace(".js", "")
        module_name_title = module_name.replace("_", " ").title().replace(" ", "")
        
        # Build imports/requires section
        imports = []
        
        # Add related imports based on context
        if "express" in context["imports"]:
            imports.append("const express = require('express');")
            
        if "fs" in context["imports"] or any("file" in req.lower() for req in requirements):
            imports.append("const fs = require('fs');")
            
        if "path" in context["imports"]:
            imports.append("const path = require('path');")
            
        # Build class definition
        class_def = [
            f"/**",
            f" * {module_name_title} for Benton County Assessor's Office AI Platform",
            f" * ",
            f" * This component implements functionality to handle {module_name} operations.",
            f" */",
            f"class {module_name_title} {{",
            f"  /**",
            f"   * Initialize the {module_name_title}.",
            f"   * @param {{Object}} config - Configuration options",
            f"   */",
            f"  constructor(config) {{",
            f"    this.config = config || {{}};",
            f"    this.logger = console;",
            f"  }}",
            f"}}"
        ]
        
        # Add methods based on requirements
        methods = []
        for req in requirements:
            method_name = self._extract_method_name(req)
            if method_name:
                methods.append(self._generate_js_method(method_name, req))
                
        # If no methods extracted, add a generic one
        if not methods:
            methods.append(self._generate_js_method("process", "Process data according to configuration"))
            
        # Insert methods before the closing bracket
        class_def_with_methods = class_def[:-1] + methods + [class_def[-1]]
        
        # Export the class
        exports = [
            "",
            "module.exports = {module_name_title};"
        ]
        
        # Combine everything
        code = "\n".join(imports + [""] + class_def_with_methods + exports)
        
        return code
    
    def _generate_html_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """Generate HTML code."""
        page_title = os.path.basename(output_file).replace(".html", "").replace("_", " ").title()
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title} - Benton County Assessor's Office</title>
    <link rel="stylesheet" href="/static/css/styles.css">
</head>
<body>
    <header>
        <h1>{page_title}</h1>
    </header>
    <main>
        <section>
            <h2>Content</h2>
            <p>This page will display {page_title.lower()} information.</p>
        </section>
    </main>
    <footer>
        <p>&copy; {datetime.now().year} Benton County Assessor's Office</p>
    </footer>
    <script src="/static/js/main.js"></script>
</body>
</html>
"""
    
    def _generate_css_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """Generate CSS code."""
        component = os.path.basename(output_file).replace(".css", "").replace("_", "-")
        
        return f"""/* 
 * {component.replace("-", " ").title()} Styles
 * Benton County Assessor's Office AI Platform
 */

.{component} {{
    display: flex;
    flex-direction: column;
    margin: 1rem 0;
    padding: 1rem;
    border-radius: 4px;
    background-color: #f5f5f5;
}}

.{component}-header {{
    font-size: 1.2rem;
    font-weight: bold;
    margin-bottom: 0.5rem;
}}

.{component}-content {{
    display: flex;
    flex-wrap: wrap;
    gap: 1rem;
}}

.{component}-item {{
    flex: 1;
    min-width: 200px;
    padding: 0.5rem;
    border: 1px solid #ddd;
    border-radius: 4px;
    background-color: white;
}}

@media (max-width: 768px) {{
    .{component}-content {{
        flex-direction: column;
    }}
}}
"""
    
    def _generate_generic_code(
        self, 
        requirements: List[str], 
        context: Dict[str, Any], 
        output_file: str
    ) -> str:
        """Generate generic code."""
        filename = os.path.basename(output_file)
        
        return f"""# {filename}
# Benton County Assessor's Office AI Platform

# This file is auto-generated to implement the following requirements:
{chr(10).join([f'# - {req}' for req in requirements])}

# Implementation to be completed
"""
    
    def _extract_method_name(self, requirement: str) -> Optional[str]:
        """
        Extract method name from a requirement description.
        
        Args:
            requirement: Requirement description
            
        Returns:
            Method name or None
        """
        # Look for verbs followed by objects
        verb_patterns = [
            r"(?:implement|create|add|generate)\s+(?:a|an)?\s*([a-z_]+(?:\s+[a-z_]+){0,3})",
            r"(?:should|must|will)\s+(?:be able to\s+)?([a-z_]+(?:\s+[a-z_]+){0,3})",
            r"^([a-z_]+(?:\s+[a-z_]+){0,3})\s+(?:functionality|function|method)"
        ]
        
        for pattern in verb_patterns:
            matches = re.search(pattern, requirement.lower())
            if matches:
                method_text = matches.group(1).strip()
                method_name = method_text.replace(" ", "_")
                return method_name
                
        # Return None if no pattern matched
        return None
    
    def _generate_method(self, method_name: str, description: str) -> str:
        """
        Generate a Python method.
        
        Args:
            method_name: Method name
            description: Method description
            
        Returns:
            Generated method code
        """
        method = [
            f"    def {method_name}(self, data: Dict[str, Any]) -> Dict[str, Any]:",
            f'        """',
            f"        {description}",
            f"        ",
            f"        Args:",
            f"            data: Input data",
            f"            ",
            f"        Returns:",
            f"            Processed data",
            f'        """',
            f"        self.logger.info(f'Processing data with {method_name}')",
            f"        ",
            f"        # TODO: Implement {description.lower()}",
            f"        result = {{",
            f"            'status': 'success',",
            f"            'message': '{description} completed',",
            f"            'data': data",
            f"        }}",
            f"        ",
            f"        return result"
        ]
        
        return "\n".join(method)
    
    def _generate_js_method(self, method_name: str, description: str) -> str:
        """
        Generate a JavaScript method.
        
        Args:
            method_name: Method name
            description: Method description
            
        Returns:
            Generated method code
        """
        # Convert snake_case to camelCase
        parts = method_name.split('_')
        js_method_name = parts[0] + ''.join(p.title() for p in parts[1:])
        
        method = [
            f"  /**",
            f"   * {description}",
            f"   * @param {{Object}} data - Input data",
            f"   * @return {{Object}} Processed data",
            f"   */",
            f"  {js_method_name}(data) {{",
            f"    this.logger.info(`Processing data with {js_method_name}`);",
            f"    ",
            f"    // TODO: Implement {description.toLowerCase()}",
            f"    const result = {{",
            f"      status: 'success',",
            f"      message: '{description} completed',",
            f"      data",
            f"    }};",
            f"    ",
            f"    return result;",
            f"  }}"
        ]
        
        return "\n".join(method)
    
    def _review_code(self, file_path: str, code: str, review_type: str) -> Dict[str, Any]:
        """
        Review code for issues and improvement opportunities.
        
        Args:
            file_path: File path
            code: Code to review
            review_type: Type of review (general, security, performance)
            
        Returns:
            Review results
        """
        # This is a placeholder for actual code review logic
        issues = []
        improvements = []
        ext = os.path.splitext(file_path)[1].lower()
        
        # Check code length
        if len(code) > 10000:
            issues.append({
                "severity": "medium",
                "type": "complexity",
                "message": "File is very large and may need to be refactored into smaller modules"
            })
        
        # Check Python-specific issues
        if ext == ".py":
            # Check for missing docstrings
            if '"""' not in code:
                issues.append({
                    "severity": "low",
                    "type": "documentation",
                    "message": "Missing module or class docstrings"
                })
                
            # Check for exception handling
            if "except:" in code and "except Exception:" not in code:
                issues.append({
                    "severity": "medium",
                    "type": "error_handling",
                    "message": "Bare except clause should catch more specific exceptions"
                })
                
            # Check for logging
            if "import logging" in code and "logger =" not in code:
                improvements.append({
                    "type": "logging",
                    "message": "Add proper logger initialization and use"
                })
        
        # Check JavaScript-specific issues
        elif ext == ".js":
            # Check for console.log
            if "console.log" in code:
                improvements.append({
                    "type": "debugging",
                    "message": "Replace console.log with proper logging mechanism"
                })
                
            # Check for var
            if re.search(r"\bvar\b", code):
                improvements.append({
                    "type": "modernization",
                    "message": "Replace 'var' with 'const' or 'let'"
                })
        
        # Check for TODO comments
        todos = re.findall(r"# ?TODO|// ?TODO", code)
        if todos:
            improvements.append({
                "type": "implementation",
                "message": f"Implement {len(todos)} TODO items"
            })
        
        # Add review summary
        summary = {
            "file_path": file_path,
            "issues": issues,
            "improvements": improvements,
            "issue_count": len(issues),
            "improvement_count": len(improvements),
            "overall_assessment": "good" if len(issues) == 0 else "needs_improvement"
        }
        
        return summary
    
    def _generate_test_code(self, file_path: str, code: str) -> str:
        """
        Generate test code for a source file.
        
        Args:
            file_path: Source file path
            code: Source code
            
        Returns:
            Generated test code
        """
        # Extract module name and classes/functions
        module_name = os.path.basename(file_path).replace(".py", "")
        
        # Extract classes
        class_pattern = r"class\s+(\w+)\s*(?:\(.*\))?\s*:"
        classes = re.findall(class_pattern, code)
        
        # Extract functions (outside classes)
        func_pattern = r"^def\s+(\w+)\s*\("
        funcs = re.findall(func_pattern, code, re.MULTILINE)
        
        # Generate test code
        if classes:
            return self._generate_class_tests(module_name, classes, file_path)
        else:
            return self._generate_function_tests(module_name, funcs, file_path)
    
    def _generate_class_tests(self, module_name: str, classes: List[str], file_path: str) -> str:
        """
        Generate test code for classes.
        
        Args:
            module_name: Module name
            classes: List of class names
            file_path: Source file path
            
        Returns:
            Generated test code
        """
        import_path = file_path.replace("/", ".").replace(".py", "")
        
        # Generate test file structure
        test_code = [
            '"""',
            f"Tests for {module_name} module.",
            '"""',
            "",
            "import unittest",
            f"from {import_path} import {', '.join(classes)}",
            "",
            "",
        ]
        
        # Generate test classes
        for class_name in classes:
            test_code.extend([
                f"class Test{class_name}(unittest.TestCase):",
                '    """',
                f"    Tests for {class_name} class.",
                '    """',
                "",
                "    def setUp(self):",
                '        """Set up test fixtures."""',
                f"        self.{module_name} = {class_name}()",
                "",
                "    def tearDown(self):",
                '        """Tear down test fixtures."""',
                "        pass",
                "",
                "    def test_initialization(self):",
                '        """Test initialization."""',
                f"        self.assertIsInstance(self.{module_name}, {class_name})",
                "",
                "    # Add more test methods here",
                "",
                "",
            ])
        
        # Add main block
        test_code.extend([
            "if __name__ == '__main__':",
            "    unittest.main()",
            ""
        ])
        
        return "\n".join(test_code)
    
    def _generate_function_tests(self, module_name: str, funcs: List[str], file_path: str) -> str:
        """
        Generate test code for functions.
        
        Args:
            module_name: Module name
            funcs: List of function names
            file_path: Source file path
            
        Returns:
            Generated test code
        """
        import_path = file_path.replace("/", ".").replace(".py", "")
        
        # Generate test file structure
        test_code = [
            '"""',
            f"Tests for {module_name} module.",
            '"""',
            "",
            "import unittest",
            f"from {import_path} import {', '.join(funcs) if funcs else '*'}",
            "",
            "",
            f"class Test{module_name.title()}(unittest.TestCase):",
            '    """',
            f"    Tests for {module_name} module.",
            '    """',
            "",
            "    def setUp(self):",
            '        """Set up test fixtures."""',
            "        pass",
            "",
            "    def tearDown(self):",
            '        """Tear down test fixtures."""',
            "        pass",
            "",
        ]
        
        # Generate test methods for each function
        for func in funcs:
            test_code.extend([
                f"    def test_{func}(self):",
                f'        """Test {func} function."""',
                f"        # TODO: Implement test for {func}",
                f"        # result = {func}(...)",
                f"        # self.assertIsNotNone(result)",
                "",
            ])
        
        # If no functions found, add a placeholder test
        if not funcs:
            test_code.extend([
                "    def test_module(self):",
                '        """Test that the module can be imported."""',
                f"        self.assertTrue(hasattr(unittest.modules['{import_path}'], '__file__'))",
                "",
            ])
        
        # Add main block
        test_code.extend([
            "",
            "if __name__ == '__main__':",
            "    unittest.main()",
            ""
        ])
        
        return "\n".join(test_code)
    
    def _generate_documentation(self, subject: str, doc_type: str) -> Dict[str, Any]:
        """
        Generate documentation for a subject.
        
        Args:
            subject: Subject to document
            doc_type: Type of documentation (function, class, module)
            
        Returns:
            Generated documentation
        """
        # This is a placeholder for actual documentation generation logic
        if doc_type == "function":
            return {
                "docstring": self._generate_function_docstring(subject),
                "examples": self._generate_examples(subject),
                "subject": subject,
                "type": doc_type
            }
        elif doc_type == "class":
            return {
                "docstring": self._generate_class_docstring(subject),
                "examples": self._generate_examples(subject),
                "subject": subject,
                "type": doc_type
            }
        elif doc_type == "module":
            return {
                "docstring": self._generate_module_docstring(subject),
                "examples": self._generate_examples(subject),
                "subject": subject,
                "type": doc_type
            }
        else:
            return {
                "error": f"Unsupported documentation type: {doc_type}"
            }
    
    def _generate_function_docstring(self, function_name: str) -> str:
        """Generate a docstring for a function."""
        return f"""
{function_name} function.

This function performs operations related to {function_name.replace("_", " ")}.

Args:
    param1: First parameter
    param2: Second parameter
    
Returns:
    Operation result
    
Raises:
    ValueError: If parameters are invalid
"""
    
    def _generate_class_docstring(self, class_name: str) -> str:
        """Generate a docstring for a class."""
        return f"""
{class_name} class.

This class implements functionality for {class_name}.

Attributes:
    attr1: First attribute
    attr2: Second attribute
"""
    
    def _generate_module_docstring(self, module_name: str) -> str:
        """Generate a docstring for a module."""
        return f"""
{module_name} module.

This module provides functionality for {module_name.replace("_", " ")}.

Example:
    ```python
    import {module_name}
    
    result = {module_name}.process(data)
    ```
"""
    
    def _generate_examples(self, subject: str) -> List[Dict[str, str]]:
        """Generate usage examples."""
        return [
            {
                "title": f"Basic usage of {subject}",
                "code": f"# Example of using {subject}\nresult = {subject}(data)"
            },
            {
                "title": f"Advanced usage of {subject}",
                "code": f"# Advanced example\nconfig = {{\n    'option': 'value'\n}}\nresult = {subject}(data, config=config)"
            }
        ]
    
    def _generate_readme(self, description: str, related_files: List[str]) -> str:
        """
        Generate a README file.
        
        Args:
            description: Project description
            related_files: Related files
            
        Returns:
            README content
        """
        # Extract project name from directory or first file
        if related_files:
            project_name = os.path.basename(os.path.dirname(related_files[0]))
            if not project_name or project_name == ".":
                project_name = os.path.basename(related_files[0]).replace(".py", "").replace("_", " ").title()
        else:
            project_name = "Benton County Assessor Project"
            
        # Extract sections from description
        sections = description.split("\n\n")
        overview = sections[0] if sections else description
        
        # Generate README content
        content = [
            f"# {project_name}",
            "",
            overview,
            "",
            "## Features",
            ""
        ]
        
        # Extract features from description
        feature_pattern = r"(?:[-*]\s*(.*?)(?=\n[-*]|\n\n|$)|\d+\.\s*(.*?)(?=\n\d+\.|\n\n|$))"
        features = re.findall(feature_pattern, description, re.DOTALL)
        
        # Flatten features and remove empty groups
        flat_features = []
        for feature_group in features:
            for feature in feature_group:
                if feature.strip():
                    flat_features.append(feature.strip())
        
        if flat_features:
            for feature in flat_features:
                content.append(f"- {feature}")
        else:
            content.append("- Feature 1")
            content.append("- Feature 2")
            
        # Add installation and usage sections
        content.extend([
            "",
            "## Installation",
            "",
            "```bash",
            "# Clone the repository",
            "git clone https://github.com/your-organization/benton-county-project.git",
            "",
            "# Change to the project directory",
            "cd benton-county-project",
            "",
            "# Install dependencies",
            "pip install -r requirements.txt",
            "```",
            "",
            "## Usage",
            "",
            "```python",
            "# Example usage code",
            "from project import main",
            "",
            "main.run()",
            "```",
            "",
            "## License",
            "",
            "This project is licensed under the terms of the license provided by Benton County Assessor's Office.",
            "",
            "## Contact",
            "",
            "For questions or support, please contact the Benton County Assessor's Office."
        ])
        
        return "\n".join(content)
    
    def _improve_docstrings(self, file_path: str, code: str) -> str:
        """
        Improve docstrings in code.
        
        Args:
            file_path: File path
            code: Source code
            
        Returns:
            Improved code
        """
        # This is a placeholder for actual docstring improvement logic
        # In a real implementation, this would parse the code and add or improve docstrings
        
        improved_code = code
        
        # Check if module has a docstring
        if not code.startswith('"""') and not code.startswith('\'\'\''):
            module_name = os.path.basename(file_path).replace(".py", "").replace("_", " ").title()
            module_docstring = f'"""\n{module_name} Module\n\nThis module provides functionality for {module_name.lower()}.\n"""\n\n'
            improved_code = module_docstring + improved_code
            
        # Add simple docstrings to classes and methods
        # Note: This is a very simplistic approach and would need more sophisticated parsing in a real implementation
        class_pattern = r"^class\s+(\w+)(?:\(.*\))?\s*:\s*(?:(?!''')(?!\"\"\").)*((?:\'\'\'|\"\"\").*?(?:\'\'\'|\"\"\"))?(?:\s*\n\s*|$)"
        improved_code = re.sub(
            class_pattern,
            lambda m: f"class {m.group(1)}{m.group(0)[len(f'class {m.group(1)}'):m.group(0).index(':') + 1]}\n    \"\"\"\n    {m.group(1)} class.\n    \"\"\"\n    ",
            improved_code,
            flags=re.DOTALL | re.MULTILINE
        )
        
        # Add simple docstrings to functions
        func_pattern = r"^def\s+(\w+)(?:\(.*\))?\s*:\s*(?:(?!''')(?!\"\"\").)*((?:\'\'\'|\"\"\").*?(?:\'\'\'|\"\"\"))?(?:\s*\n\s*|$)"
        improved_code = re.sub(
            func_pattern,
            lambda m: f"def {m.group(1)}{m.group(0)[len(f'def {m.group(1)}'):m.group(0).index(':') + 1]}\n    \"\"\"\n    {m.group(1)} function.\n    \"\"\"\n    ",
            improved_code,
            flags=re.DOTALL | re.MULTILINE
        )
        
        return improved_code
    
    def _improve_code(self, file_path: str, code: str, description: str) -> str:
        """
        Improve code based on description.
        
        Args:
            file_path: File path
            code: Source code
            description: Improvement description
            
        Returns:
            Improved code
        """
        # This is a placeholder for actual code improvement logic
        improved_code = code
        
        # Check if we need to fix line length
        if "line-too-long" in description.lower():
            # Simplistic line wrapping
            lines = improved_code.split("\n")
            improved_lines = []
            
            for line in lines:
                if len(line) > 100 and not line.strip().startswith("#") and not line.strip().startswith("\"\"\""):
                    # Try to break at logical points
                    if "," in line[50:]:
                        pos = line.find(",", 50) + 1
                        improved_lines.append(line[:pos])
                        improved_lines.append(" " * (len(line) - len(line.lstrip())) + line[pos:].lstrip())
                    elif " = " in line:
                        improved_lines.append(line)  # Keep assignment lines as-is for now
                    else:
                        improved_lines.append(line)  # Keep other lines as-is for now
                else:
                    improved_lines.append(line)
                    
            improved_code = "\n".join(improved_lines)
            
        # Add TODOs to implementation if requested
        if "todo" in description.lower():
            # Replace existing TODOs with implementation
            todo_pattern = r"# ?TODO:? (.*)"
            improved_code = re.sub(
                todo_pattern,
                lambda m: f"# Implemented: {m.group(1)}\n    pass",
                improved_code
            )
            
        return improved_code
    
    def _send_task_update(
        self, 
        task_id: str, 
        status: str, 
        result: Optional[Dict[str, Any]] = None,
        message_id: Optional[str] = None,
        correlation_id: Optional[str] = None,
        source_agent_id: str = "agent_coordinator"
    ) -> None:
        """
        Send a task update message.
        
        Args:
            task_id: Task ID
            status: New status
            result: Task result
            message_id: Original message ID
            correlation_id: Correlation ID
            source_agent_id: Target agent ID
        """
        command = CommandMessage(
            source_agent_id=self.agent_id,
            target_agent_id=source_agent_id,
            command_name="update_task_status",
            parameters={
                "task_id": task_id,
                "status": status,
                "result": result
            }
        )
        
        self.send_message(command)
        self.logger.info(f"Sent task update for task {task_id} with status {status}")
    
    def _submit_code_contribution(self, task_id: str, file_path: str, code: str) -> None:
        """
        Submit a code contribution.
        
        Args:
            task_id: Task ID
            file_path: File path
            code: Code
        """
        command = CommandMessage(
            source_agent_id=self.agent_id,
            target_agent_id="agent_coordinator",
            command_name="submit_code_contribution",
            parameters={
                "task_id": task_id,
                "file_path": file_path,
                "code": code
            }
        )
        
        self.send_message(command)
        self.logger.info(f"Submitted code contribution for task {task_id}: {file_path}")
    
    def _send_error_response(self, message: Message, error_code: str, error_message: str) -> None:
        """
        Send an error response message.
        
        Args:
            message: Original message
            error_code: Error code
            error_message: Error message
        """
        error = ErrorMessage(
            source_agent_id=self.agent_id,
            target_agent_id=message.source_agent_id,
            error_code=error_code,
            error_message=error_message,
            correlation_id=message.correlation_id
        )
        
        self.send_message(error)
        self.logger.warning(f"Sent error response: {error_code} - {error_message}")


def create_developer_agent(agent_id: str, config_path: Optional[str] = None) -> DeveloperAgent:
    """
    Create a Developer Agent with the specified configuration.
    
    Args:
        agent_id: Agent ID
        config_path: Path to configuration file
        
    Returns:
        Configured Developer Agent
    """
    if config_path and os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = json.load(f)
    else:
        config = {
            "specialization": "full_stack",
            "code_generation_mode": "incremental",
            "log_level": "info"
        }
    
    return DeveloperAgent(agent_id, config)