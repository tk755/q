"""
Comprehensive unit tests for command registry system.

Tests the command registration, discovery, and validation functionality including:
- Command registration and lookup
- Flag conflict detection
- Default command handling
- Command validation
- Registry management
"""

import pytest
from unittest.mock import Mock
from typing import List

from q.commands.registry import (
    register_command, get_command, get_default_command,
    list_commands, get_all_flags, validate_commands,
    _commands, _command_classes
)
from q.commands.base import BaseCommand
from q.config.models import Message, MessageRole, ModelParameters
from q.utils.exceptions import ValidationError


# Test command classes for testing
class TestCommand1(BaseCommand):
    """Test command with flags."""
    
    def __init__(self):
        self._flags = ['-t1', '--test1']
        self._description = "Test command 1"
        self._clip_output = False
    
    @property
    def flags(self) -> List[str]:
        return self._flags
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def clip_output(self) -> bool:
        return self._clip_output
    
    def get_messages(self, text: str) -> List[Message]:
        return [Message(MessageRole.USER, f"Test1: {text}")]
    
    def get_model_params(self) -> ModelParameters:
        return ModelParameters(model='test-model-1')


class TestCommand2(BaseCommand):
    """Another test command with flags."""
    
    def __init__(self):
        self._flags = ['-t2', '--test2']
        self._description = "Test command 2"
        self._clip_output = True
    
    @property
    def flags(self) -> List[str]:
        return self._flags
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def clip_output(self) -> bool:
        return self._clip_output
    
    def get_messages(self, text: str) -> List[Message]:
        return [Message(MessageRole.USER, f"Test2: {text}")]
    
    def get_model_params(self) -> ModelParameters:
        return ModelParameters(model='test-model-2')


class TestDefaultCommand(BaseCommand):
    """Test default command (no flags)."""
    
    def __init__(self):
        self._flags = []
        self._description = "Default test command"
        self._clip_output = False
    
    @property
    def flags(self) -> List[str]:
        return self._flags
    
    @property
    def description(self) -> str:
        return self._description
    
    @property
    def clip_output(self) -> bool:
        return self._clip_output
    
    def get_messages(self, text: str) -> List[Message]:
        return [Message(MessageRole.USER, f"Default: {text}")]
    
    def get_model_params(self) -> ModelParameters:
        return ModelParameters(model='default-model')


class InvalidCommand:
    """Invalid command that doesn't inherit from BaseCommand."""
    
    def __init__(self):
        self.flags = ['-invalid']


class FailingCommand(BaseCommand):
    """Command that fails during instantiation."""
    
    def __init__(self):
        raise Exception("Instantiation failed")
    
    @property
    def flags(self) -> List[str]:
        return ['-failing']
    
    @property
    def description(self) -> str:
        return "Failing command"
    
    @property
    def clip_output(self) -> bool:
        return False
    
    def get_messages(self, text: str) -> List[Message]:
        return []
    
    def get_model_params(self) -> ModelParameters:
        return ModelParameters()


@pytest.mark.unit
class TestCommandRegistry:
    """Test command registry functionality."""
    
    def setup_method(self):
        """Clear registry before each test."""
        _commands.clear()
        _command_classes.clear()
    
    def test_register_valid_command(self):
        """Test registering a valid command."""
        register_command(TestCommand1)
        
        # Check that command is registered
        assert '-t1' in _commands
        assert '--test1' in _commands
        assert 'TestCommand1' in _command_classes
        
        # Check that we can retrieve it
        cmd = get_command('-t1')
        assert cmd is not None
        assert isinstance(cmd, TestCommand1)
        
        cmd = get_command('--test1')
        assert cmd is not None
        assert isinstance(cmd, TestCommand1)
        
        # Should be the same instance
        assert get_command('-t1') is get_command('--test1')
    
    def test_register_default_command(self):
        """Test registering a default command (no flags)."""
        register_command(TestDefaultCommand)
        
        # Check that default command is registered
        assert '' in _commands
        assert 'TestDefaultCommand' in _command_classes
        
        # Check that we can retrieve it
        default_cmd = get_default_command()
        assert default_cmd is not None
        assert isinstance(default_cmd, TestDefaultCommand)
    
    def test_register_multiple_commands(self):
        """Test registering multiple commands."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        register_command(TestDefaultCommand)
        
        # Check that all commands are registered
        assert len(_commands) == 5  # 2 + 2 + 1 flags
        assert len(_command_classes) == 3
        
        # Check that we can retrieve all of them
        cmd1 = get_command('-t1')
        cmd2 = get_command('-t2')
        default_cmd = get_default_command()
        
        assert isinstance(cmd1, TestCommand1)
        assert isinstance(cmd2, TestCommand2)
        assert isinstance(default_cmd, TestDefaultCommand)
    
    def test_register_invalid_command_class(self):
        """Test registering an invalid command class."""
        with pytest.raises(ValidationError, match="must implement BaseCommand interface"):
            register_command(InvalidCommand)
    
    def test_register_failing_command_class(self):
        """Test registering a command class that fails during instantiation."""
        with pytest.raises(ValidationError, match="Failed to instantiate command class"):
            register_command(FailingCommand)
    
    def test_register_conflicting_flags(self):
        """Test registering commands with conflicting flags."""
        # Register first command
        register_command(TestCommand1)
        
        # Create a command with conflicting flag
        class ConflictingCommand(BaseCommand):
            @property
            def flags(self) -> List[str]:
                return ['-t1']  # Conflicts with TestCommand1
            
            @property
            def description(self) -> str:
                return "Conflicting command"
            
            @property
            def clip_output(self) -> bool:
                return False
            
            def get_messages(self, text: str) -> List[Message]:
                return []
            
            def get_model_params(self) -> ModelParameters:
                return ModelParameters()
        
        with pytest.raises(ValidationError, match="Flag '-t1' is already registered"):
            register_command(ConflictingCommand)
    
    def test_get_nonexistent_command(self):
        """Test getting a command that doesn't exist."""
        assert get_command('-nonexistent') is None
        assert get_command('--nonexistent') is None
    
    def test_get_default_command_when_none(self):
        """Test getting default command when none is registered."""
        assert get_default_command() is None
    
    def test_list_commands(self):
        """Test listing all registered commands."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        register_command(TestDefaultCommand)
        
        commands = list_commands()
        
        assert len(commands) == 3
        command_types = [type(cmd).__name__ for cmd in commands]
        assert 'TestCommand1' in command_types
        assert 'TestCommand2' in command_types
        assert 'TestDefaultCommand' in command_types
    
    def test_list_commands_unique_instances(self):
        """Test that list_commands returns unique instances even with multiple flags."""
        register_command(TestCommand1)  # Has 2 flags: -t1, --test1
        
        commands = list_commands()
        
        # Should only return one instance even though command has 2 flags
        assert len(commands) == 1
        assert isinstance(commands[0], TestCommand1)
    
    def test_get_all_flags(self):
        """Test getting all registered flags."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        register_command(TestDefaultCommand)
        
        flags = get_all_flags()
        
        expected_flags = ['-t1', '--test1', '-t2', '--test2', '']
        assert set(flags) == set(expected_flags)
    
    def test_validate_commands_success(self):
        """Test command validation with valid setup."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        register_command(TestDefaultCommand)
        
        errors = validate_commands()
        
        assert len(errors) == 0
    
    def test_validate_commands_no_default(self):
        """Test command validation when no default command is registered."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        # No default command
        
        errors = validate_commands()
        
        assert len(errors) == 1
        assert "No default command found" in errors[0]
    
    def test_validate_commands_multiple_defaults(self):
        """Test command validation with multiple default commands."""
        register_command(TestDefaultCommand)
        
        # Register another default command directly (bypassing normal registration)
        another_default = TestDefaultCommand()
        _commands[''] = another_default  # This would create the conflict
        
        # Manually add to list to simulate the issue
        class AnotherDefaultCommand(BaseCommand):
            @property
            def flags(self) -> List[str]:
                return []
            
            @property
            def description(self) -> str:
                return "Another default"
            
            @property
            def clip_output(self) -> bool:
                return False
            
            def get_messages(self, text: str) -> List[Message]:
                return []
            
            def get_model_params(self) -> ModelParameters:
                return ModelParameters()
        
        # Add to registry bypassing normal registration to create conflict
        another_cmd = AnotherDefaultCommand()
        _command_classes['AnotherDefaultCommand'] = AnotherDefaultCommand
        
        # Simulate having multiple default commands in the list
        original_list_commands = list_commands
        
        def mock_list_commands():
            return [TestDefaultCommand(), AnotherDefaultCommand()]
        
        # Patch list_commands temporarily
        import q.commands.registry
        q.commands.registry.list_commands = mock_list_commands
        
        try:
            errors = validate_commands()
            assert len(errors) >= 1
            assert any("More than one default command found" in error for error in errors)
        finally:
            # Restore original function
            q.commands.registry.list_commands = original_list_commands
    
    def test_command_retrieval_consistency(self):
        """Test that command retrieval is consistent."""
        register_command(TestCommand1)
        
        # Multiple retrievals should return the same instance
        cmd1a = get_command('-t1')
        cmd1b = get_command('-t1')
        cmd1c = get_command('--test1')
        
        assert cmd1a is cmd1b is cmd1c
    
    def test_registry_state_isolation(self):
        """Test that registry state is properly managed."""
        # Start with empty registry
        assert len(_commands) == 0
        assert len(_command_classes) == 0
        
        # Register command
        register_command(TestCommand1)
        assert len(_commands) == 2  # Two flags
        assert len(_command_classes) == 1
        
        # Clear registry
        _commands.clear()
        _command_classes.clear()
        
        # Should be empty again
        assert len(_commands) == 0
        assert len(_command_classes) == 0
        assert get_command('-t1') is None
    
    def test_flag_lookup_case_sensitivity(self):
        """Test that flag lookup is case sensitive."""
        register_command(TestCommand1)
        
        # Exact match should work
        assert get_command('-t1') is not None
        assert get_command('--test1') is not None
        
        # Case variations should not work
        assert get_command('-T1') is None
        assert get_command('--TEST1') is None
        assert get_command('-t1 ') is None  # With space
    
    def test_command_configuration_format(self):
        """Test that commands produce proper configuration format."""
        register_command(TestCommand1)
        
        cmd = get_command('-t1')
        config = cmd.get_command_config()
        
        # Check required fields
        assert 'flags' in config
        assert 'description' in config
        assert 'clip_output' in config
        assert 'model_args' in config
        assert 'messages' in config
        
        # Check values
        assert config['flags'] == ['-t1', '--test1']
        assert config['description'] == "Test command 1"
        assert config['clip_output'] == False
        assert isinstance(config['model_args'], dict)
        assert isinstance(config['messages'], list)
    
    def test_command_message_generation(self):
        """Test that commands generate messages correctly."""
        register_command(TestCommand1)
        
        cmd = get_command('-t1')
        messages = cmd.get_messages("hello world")
        
        assert len(messages) == 1
        assert messages[0].role == MessageRole.USER
        assert messages[0].content == "Test1: hello world"
    
    def test_command_model_params(self):
        """Test that commands return proper model parameters."""
        register_command(TestCommand1)
        
        cmd = get_command('-t1')
        params = cmd.get_model_params()
        
        assert isinstance(params, ModelParameters)
        assert params.model == 'test-model-1'
    
    def test_registry_performance_large_number_of_commands(self):
        """Test registry performance with many commands."""
        import time
        
        # Create many test commands
        command_classes = []
        for i in range(100):
            
            class DynamicCommand(BaseCommand):
                def __init__(self, index):
                    self.index = index
                
                @property
                def flags(self) -> List[str]:
                    return [f'-d{self.index}', f'--dynamic{self.index}']
                
                @property
                def description(self) -> str:
                    return f"Dynamic command {self.index}"
                
                @property
                def clip_output(self) -> bool:
                    return False
                
                def get_messages(self, text: str) -> List[Message]:
                    return [Message(MessageRole.USER, f"Dynamic{self.index}: {text}")]
                
                def get_model_params(self) -> ModelParameters:
                    return ModelParameters(model=f'dynamic-model-{self.index}')
            
            # Create a unique class for each command
            class_name = f'DynamicCommand{i}'
            cmd_class = type(class_name, (BaseCommand,), {
                '__init__': lambda self, idx=i: DynamicCommand.__init__(self, idx),
                'flags': property(lambda self, idx=i: [f'-d{idx}', f'--dynamic{idx}']),
                'description': property(lambda self, idx=i: f"Dynamic command {idx}"),
                'clip_output': property(lambda self: False),
                'get_messages': lambda self, text, idx=i: [Message(MessageRole.USER, f"Dynamic{idx}: {text}")],
                'get_model_params': lambda self, idx=i: ModelParameters(model=f'dynamic-model-{idx}')
            })
            
            command_classes.append(cmd_class)
        
        # Register all commands
        start_time = time.time()
        for cmd_class in command_classes:
            register_command(cmd_class)
        registration_time = time.time() - start_time
        
        # Lookup commands
        start_time = time.time()
        for i in range(100):
            cmd = get_command(f'-d{i}')
            assert cmd is not None
        lookup_time = time.time() - start_time
        
        # List all commands
        start_time = time.time()
        commands = list_commands()
        list_time = time.time() - start_time
        
        # Performance assertions (should be fast)
        assert registration_time < 1.0  # Should register 100 commands in under 1 second
        assert lookup_time < 0.1  # Should lookup 100 commands in under 0.1 seconds
        assert list_time < 0.1  # Should list all commands in under 0.1 seconds
        assert len(commands) == 100


@pytest.mark.integration
class TestCommandRegistryIntegration:
    """Integration tests for command registry."""
    
    def setup_method(self):
        """Clear registry before each test."""
        _commands.clear()
        _command_classes.clear()
    
    def test_integration_with_real_commands(self):
        """Test registry integration with actual command implementations."""
        # Import and register actual commands
        from q.commands.explain import ExplainCommand
        from q.commands.code import CodeCommand
        from q.commands.default import DefaultCommand
        
        register_command(ExplainCommand)
        register_command(CodeCommand)  
        register_command(DefaultCommand)
        
        # Test retrieval
        explain_cmd = get_command('-e')
        code_cmd = get_command('--code')
        default_cmd = get_default_command()
        
        assert explain_cmd is not None
        assert code_cmd is not None
        assert default_cmd is not None
        
        # Test that they work
        explain_msgs = explain_cmd.get_messages("What is Python?")
        code_msgs = code_cmd.get_messages("Sort a list")
        default_msgs = default_cmd.get_messages("Hello")
        
        assert len(explain_msgs) > 0
        assert len(code_msgs) > 0  
        assert len(default_msgs) > 0
        
        # Test validation
        errors = validate_commands()
        assert len(errors) == 0
    
    def test_command_discovery_workflow(self):
        """Test complete command discovery workflow."""
        register_command(TestCommand1)
        register_command(TestCommand2)
        register_command(TestDefaultCommand)
        
        # Simulate CLI argument parsing workflow
        test_args = ['-t1', '--test2', 'some_text']
        
        # Find which commands match
        all_flags = get_all_flags()
        matching_flags = [arg for arg in test_args if arg in all_flags]
        
        assert '-t1' in matching_flags
        assert '--test2' in matching_flags
        
        # Get the commands
        for flag in matching_flags:
            cmd = get_command(flag)
            assert cmd is not None
            
            # Test that command can generate config
            config = cmd.get_command_config()
            assert 'flags' in config
            assert 'description' in config