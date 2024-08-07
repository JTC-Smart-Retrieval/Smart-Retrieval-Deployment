import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from fastapi.websockets import WebSocketDisconnect
from llama_index.core.llms import ChatMessage
from llama_index.core.llms import MessageRole
from llama_index.core.memory import ChatMemoryBuffer
from llama_index.core import PromptTemplate
from pydantic import BaseModel

from backend.app.utils import auth
from backend.app.utils.contants import MEMORY_TOKEN_LIMIT
from backend.app.utils.index import get_index
from backend.app.utils.json import json_to_model

chat_router = r = APIRouter(dependencies=[Depends(auth.validate_user)])

"""
This router is for chatbot functionality which consist of chat memory and chat engine.
The chat memory is used to store the chat history and the chat engine is used to query the chat memory and context.
Chat engine is a wrapper around the query engine and it is used to query the chat memory and context.
Chat engine also does the following:
1. Condense the question based on the chat history
2. Add context to the question
3. Answer the question
"""


class _Message(BaseModel):
    role: MessageRole
    content: str


class _ChatData(BaseModel):
    messages: List[_Message]
    collection_id: str


# custom prompt template to be used by chat engine
custom_prompt = PromptTemplate(
    """\
Given a conversation (between Human and Assistant) and a follow up message from Human, \
rewrite the message to be a standalone question that captures all relevant context \
from the conversation.

<Chat History>
{chat_history}

<Follow Up Message>
{question}

<Standalone question>
"""
)

# list of `ChatMessage` objects
custom_chat_history = [
    ChatMessage(
        role=MessageRole.USER,
        content="Hello assistant, we are having a insightful discussion about Paul Graham today.",
    ),
    ChatMessage(role=MessageRole.ASSISTANT, content="Okay, sounds good."),
]


@r.post("")
async def chat(
    request: Request,
    # Note: To support clients sending a JSON object using content-type "text/plain",
    # we need to use Depends(json_to_model(_ChatData)) here
    data: _ChatData = Depends(json_to_model(_ChatData)),
):
    logger = logging.getLogger("uvicorn")
    # get the collection_id from the request body
    collection_id = data.collection_id
    logger.info(f"Chat -> Collection ID: {collection_id}")
    # get the index for the selected document set
    index = get_index(collection_name=collection_id)
    # check preconditions and get last message
    if len(data.messages) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No messages provided",
        )
    lastMessage = data.messages.pop()
    if lastMessage.role != MessageRole.USER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Last message must be from user",
        )
    # convert messages coming from the request to type ChatMessage
    messages = [
        ChatMessage(
            role=m.role,
            content=m.content,
        )
        for m in data.messages
    ]

    # query_engine = index.as_query_engine()
    # chat_engine = CondenseQuestionChatEngine.from_defaults(
    #     query_engine=query_engine,
    #     condense_question_prompt=custom_prompt,
    #     chat_history=custom_chat_history,
    #     verbose=True,
    # )

    logger.info(f"Messages: {messages}")

    memory = ChatMemoryBuffer.from_defaults(
        chat_history=messages,
        token_limit=MEMORY_TOKEN_LIMIT,
    )

    logger.info(f"Memory: {memory.get()}")

    # query chat engine
    chat_engine = index.as_chat_engine(
        chat_mode="condense_plus_context",
        memory=memory,
        context_prompt=(
            "You are a helpful chatbot, able to have normal interactions, as well as answer questions"
            " regarding information relating but not limited to the Public Sector Standard Conditions Of Contract (PSSCOC) Documents and JTC's Employer Information Requirements (EIR) Documents.\n"
            "PSSCOC and EIR documents are in the context of the construction industry in Singapore.\n"
            "Here are the relevant documents for the context:\n"
            "{context_str}"
            "\nInstruction: Based on the above documents, provide a detailed answer for the user question below.\n"
            "If you cannot answer the question or are unsure of how to answer, inform the user that you do not know.\n"
            "If you need to clarify the question, ask the user for clarification.\n"
            "You are to provide the relevant sources including but not limited to the file name, and page of which you got the information from in the context in brackets.\n"
            "Should there be a full file path, remove the file path and only include the file name in the context."
        ),
    )
    response = chat_engine.stream_chat(
        message=lastMessage.content, chat_history=messages
    )

    # logger.info(f"Response Sources: {response.source_nodes}")

    # stream response
    async def event_generator():
        try:
            logger = logging.getLogger("uvicorn")
            for token in response.response_gen:
                # If client closes connection, stop sending events
                if await request.is_disconnected():
                    logger.info("Client disconnected, closing stream")
                    break
                yield token
        except WebSocketDisconnect:
            # WebSocket was disconnected, gracefully handle it
            logger.info("Client disconnected, closing stream")

    logger.info(f"Chat Engine History: {chat_engine.chat_history}")

    # reset chat engine to clear memory
    chat_engine.reset()

    return StreamingResponse(event_generator(), media_type="text/plain")
