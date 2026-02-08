'''
Take inputs question and verses
return a prompt only
'''

def create_prompt(question: str, verses: list[str]):
    return f'''
        You are a Bible expert, you have spent your life studying Christian texts. 
        Please answer this question: {question}        
        Base your answer on the following verses: {verses}

        If you don't know the answer, say "I do not have a strong answer for you"
    '''