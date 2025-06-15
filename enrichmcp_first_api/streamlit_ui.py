from enum import Enum
from typing import Optional
from prompt_toolkit import print_formatted_text, HTML
import streamlit as st
import asyncio
import re

from enrichmcp_first_api.async_llm import get_chat_completion_response
from enrichmcp_first_api.model import ContextBuffer, Message, Role

import logging
import enrichmcp_first_api
from enrichmcp_first_api.lib.logger import FileLogger

# Use module root directory as log file directory
LOG: FileLogger =  FileLogger(
    log_file=f"{enrichmcp_first_api.__path__[0]}/logs/enrichmcp_first_api.log",
    level=logging.INFO,
    domain="EnrichMCPFirstAPI"
)

DIRECTIVE_RE: re.Pattern = re.compile(r'\s*\/([a-zA-Z\-]+)\s*(\d+)?(\s+\d+)?')
class GracefulExit(Exception): pass


class ContextBufferEditable(ContextBuffer):
    # Note: no seek position is maintained.

    def __init__(self, id):
        super().__init__()
        self._id = id

    @property
    def id(self) -> str:
        return self._id

    def save(self):
        LOG.info("fake saving")


def get_role_html(role: Role, prefix: str = "") -> str:
    basestr: str = ""
    if prefix:
        basestr += f'<style fg="ansiblack" bg="ansiwhite">{prefix}</style>'
    if role == Role.SYSTEM:
        return f'{basestr} <style fg="ansiwhite" bg="ansigreen">System:</style> '
    elif role == Role.USER:
        return f'{basestr} <style fg="maroon" bg="cornsilk">User:</style> '
    elif role == Role.ASSISTANT:
        return f'{basestr} <style fg="ansiwhite" bg="ansiblue">Assistant:</style> '
    elif role == Role.FUNCTION:
        return f'{basestr} <style fg="ansiwhite" bg="ansiyellow">Function:</style> '


def parse_directive(text: str) -> Optional[tuple[str, Optional[int], Optional[int]]]:
    match: re.Match = DIRECTIVE_RE.match(text)
    if match:
        groups: list[str] = match.groups()
        return groups[0], int(groups[1]) if groups[1] else None, int(groups[2]) if groups[2] else None
    return (None, None, None)


# Project


class DirectiveEnum(Enum):
    MOVE = [('move', 'm'), 'Move a message from one position to another.']
    DELETE = [('delete', 'd'), 'Delete a message.']
    SAVE = [('save', 's'), 'Save the current context.']
    SAVE_EXIT = [('exit',), 'Save the current context and exit.']
    NO_SAVE_EXIT = [('no-save-exit', 'nse'), 'Exit without saving.']
    LIST = [('list', 'l'), 'List all messages.']
    DELETE_ALL = [('delete-all',), 'Clear all messages.']
    HELP = [('help', 'h'), 'Print this help.']


def process_directive(context_buffer: ContextBuffer, directive: str, id_1: Optional[int] = None, id_2: Optional[int] = None):
    if directive in DirectiveEnum.MOVE.value[0] and id_1 is not None and id_2 is not None:
        context_buffer.move(id_1, id_2)
        print_formatted_text(f'Moved {id_1} to {id_2}.')
        print_message_list(context_buffer.list())
    elif directive in DirectiveEnum.DELETE.value[0] and id_1 is not None and id_2 is None:
        context_buffer.delete(id_1)
        print_formatted_text('Deleted.')
        print_message_list(context_buffer.list())
    elif directive in DirectiveEnum.NO_SAVE_EXIT.value[0]:
        raise GracefulExit
    elif directive in DirectiveEnum.SAVE_EXIT.value[0]:
        context_buffer.save()
        print_formatted_text('Saved.')
        raise GracefulExit
    elif directive in DirectiveEnum.SAVE.value[0]:
        context_buffer.save()
        print_formatted_text('Saved.')
    elif directive in DirectiveEnum.LIST.value[0]:
        print_message_list(context_buffer.list())
    elif directive in DirectiveEnum.DELETE_ALL.value[0]:
        context_buffer.clear()
        print_formatted_text('Cleared.')
    elif directive in DirectiveEnum.HELP.value[0]:
        print_help()
    else:
        print_formatted_text(f'Unknown directive: {directive}')    


def print_message(message: Message, prefix: str = ""):
    print_formatted_text(HTML(get_role_html(message.role, prefix=f'{prefix}: ')))
    if message.content:
        print_formatted_text(message.content)


def print_message_list(messages: list[Message]):
    if not messages:
        return
    for index, message in enumerate(messages):
        print_message(message, prefix=str(index).zfill(len(str(len(messages)))))
        print()


def print_help():
    print_formatted_text("Directives:")
    for directive in DirectiveEnum:
        print_formatted_text(f'    {" | ".join(directive.value[0])} - {directive.value[1]}')
    print_formatted_text('\nDirectives start with a / followed by a command and optionally an id (or two ids for move).')
    print_formatted_text('To submit text press ESC followed by return/enter.')


async def render_streamlit_chat(context_buffer: ContextBuffer) -> bool:
    st.markdown("## Area Chat")

    print(f"Context buffer length: {len(context_buffer)}")
    # Display chat messages from history on app rerun
    for message in context_buffer.list():
        print(message.role)
        with st.chat_message(str(message.role).lower()):
            st.markdown(message.content)

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        if not prompt or prompt.strip() == "":
            return False
        directive, id_1, id_2 = parse_directive(prompt)
        if directive:
            print("Processing directive")
            process_directive(context_buffer, directive, id_1, id_2)
        else:
            print("Running chat completion")
            # Add user message to chat history
            context_buffer.add(Message(role=Role.USER, content=prompt))
            # Display user message in chat message container
            with st.chat_message(Role.USER):
                st.markdown(prompt)

            # Display assistant response in chat message container
            with st.chat_message(Role.ASSISTANT):
                with st.spinner('Thinking...'):
                    chat_completion: str = await get_chat_completion_response(
                        messages=context_buffer.list(),
                    )
                    reply = chat_completion # TODO: flesh this out
                    context_buffer.add(Message(role=Role.ASSISTANT, content=reply))
                    context_buffer.save()

            # Add assistant response to chat history
            return True
        return False


async def main():
    #st.write("Hello, World!")
    st.button("this is a button")

    if 'controller' not in st.session_state:
        print("No controller in session state")
    if 'context_buffer' not in st.session_state:
        print("No context buffer in session state, creating new one")
        st.session_state['context_buffer'] = ContextBufferEditable(1)

    if await render_streamlit_chat(st.session_state['context_buffer']):
        st.rerun()



if __name__ == "__main__":
    asyncio.run(main())