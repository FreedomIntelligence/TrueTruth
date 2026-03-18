目标：该项目的目标是编写一个基于国际上关于循证医学通识的“5A”框架（Ask-Acquire-Appraise-Apply-Assess）的ReAct模式的python临床决策系统。
框架图：如ebm5a.png所示。五步骤基本是使用LLM来完成。
当前状况：尚未建成循证证据库，也只能使用普通LLM。
迷惑点：不太明确有哪些ReAct模块，Reason/Act/Observe的点在哪里，以及有哪些可能触发循环的门控。