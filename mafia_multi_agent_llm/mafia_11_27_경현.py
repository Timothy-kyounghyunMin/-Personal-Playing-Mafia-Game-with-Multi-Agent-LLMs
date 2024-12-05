import json
import os
import random
import time

import click
import colorama
import dotenv
import openai
from colorama import Fore, Style
from openai import OpenAI

colorama.init() # print in colors

if os.path.isfile('.env'):
    dotenv.load_dotenv()
    openai.api_key = os.getenv('OPENAI_API_KEY') # set the API key from the .env file

open_api_key=open("openApiKey.txt", encoding='utf-8').read()

class Player:
    """
    플레이어 롤마다 메모리, 프롬프트 입력 기능을 담당하는 클래스
    """
    def __init__(self, client, max_tokens, player_name, player_number, use_gpt4, output_file, user=False): ## 11/11 경현 other_players 삭제 ## 11/12 준하 수정
        self.client=client
        self.max_tokens=max_tokens
        self.player_number = player_number
        self.player_name = player_name
        #self.other_players = other_players # ? ## 11/11 경현 - 필요 없을 것 같음. 나중에 다른 부분의 other_players도 수정필요
        self.role = None # 플레이어의 진짜 역할 # mafia, doctor, police, citizen ##11/12 준하 수정
        
        self.rules_prompt_prefix = open('prompts/rules.txt').read()
        self.memory = [] # 이 게임에서의 상호작용을 기억하는 메모리
        self.use_gpt4 = use_gpt4
        self.alive = True # 플레이어가 살아있는지 여부 ## 11/11 경현
        self.user = user # 플레이어가 사람인지 AI인지 여부 ## 11/11 경현 ##11/12 준하 수정
        self.final_prompt = {}
        self.summarizer=None
        self.file_name=output_file

    def append_memory(self, role, memory_item):
        self.memory.append({'role':role, 'content':memory_item})

    def run_prompt(self, prompt, summarize=True):
        model = 'gpt-4o-mini'
        if self.user :
            return input(self.player_name+': ')
        
        # 기본 룰 프롬프트
        full_prompt = [{'role' : 'system', 'content':self.rules_prompt_prefix}]

        
        # 역할 별 프롬프트
        full_prompt.append({'role':'system', 'content':open('prompts/'+self.role+'.txt',encoding='utf-8').read()}) ##11/12 준하
            
        full_prompt=full_prompt+self.memory
        if summarize:#summarize+strategy
            summarize_prompt=full_prompt+[{'role':'user', 'content':f'Your name is {self.player_name}, your role is {self.role}. Summarize the situation so far by focusing on the peculiarities. within 100 tokens.'}]
            summary=self.client.chat.completions.create(model=model, temperature=1, messages=summarize_prompt, max_completion_tokens=100).choices[0].message.content
            strategy_prompt=full_prompt+[{'role':'user', 'content':f'Your name is {self.player_name}, your role is {self.role}. This is summary of history.\n{summary}\n Think an appropriate strategy within 100 tokens.'}]
            strategy=self.client.chat.completions.create(model=model, temperature=1, messages=strategy_prompt, max_completion_tokens=100).choices[0].message.content
            full_prompt.append({'role':'assistant', 'content':f'Summary : {summary}\nStrategy : {strategy}'})
        full_prompt=full_prompt+[{'role':'system','content':str(self.final_prompt)}]
        full_prompt.append({'role':'system', 'content':f'Your name is {self.player_name}, your role is {self.role}. You have to say only your answer. Don\'t use name label.'})

        if prompt:
            full_prompt.append(prompt)

        #full_prompt += prompt+" (Make an appropriate statement by referring to your memory. Don't use anything that's not in memory as a basis.)"

        model = 'gpt-3.5-turbo' if not self.use_gpt4 else 'gpt-4'
        model = 'gpt-4o-mini'

        # while True:
        #     completion = self.client.chat.completions.create(model=model, temperature=1, messages=full_prompt, max_completion_tokens=self.max_tokens)
        #     response = completion.choices[0].message.content
        #     if ':' not in response[0:min(20,len(response))]:
        #         break
        #     print('again')

        ### 11/27 경현 - contemplation 적용
        while True:
            completion1 = self.client.chat.completions.create(model=model, temperature=1, messages=full_prompt, max_completion_tokens=self.max_tokens)
            response1 = completion1.choices[0].message.content
            #self.append_players_memory(self.player_name, response1, self.players_summarizers)
            full_prompt.append({'role':'user', 'content':response1})
            contemplation = 'Review the utterance you just provided to determine whether it aligns with your role, complies with the game rules, and is a well-reasoned response. If there are any aspects that need improvement, revise the response and answer again.'
            #self.append_players_memory('system', contemplation, self.players_summarizers)
            full_prompt.append({'role':'system', 'content':f'Your name is {self.player_name}, your role is {self.role}. {contemplation}'})
            completion2 = self.client.chat.completions.create(model=model, temperature=1, messages=full_prompt, max_completion_tokens=self.max_tokens)
            response = completion2.choices[0].message.content

            if ':' not in response[0:min(20,len(response))]:
                break
            print('again')

        # #기록
        # with open(self.file_name, 'a') as json_file:
        #     if summarize:
        #         json.dump(f'{self.player_name}\'s Summary: {summary}', json_file)
        #         json_file.write('\n')
        #         json.dump(f'{self.player_name}\'s Strategy: {strategy}', json_file)
        #         json_file.write('\n')    
        #     json.dump(f'{self.player_name}\'s Final Utterance: {completion.choices[0].message.content}', json_file)
        #     json_file.write('\n')
        # return completion.choices[0].message.content

        #기록 - ### 11/27 경현 - contemplation 적용
        with open(self.file_name, 'a') as json_file:
            if summarize:
                json.dump(f'{self.player_name}\'s Summary: {summary}', json_file)
                json_file.write('\n')
                json.dump(f'{self.player_name}\'s Strategy: {strategy}', json_file)
                json_file.write('\n')    
            json.dump(f'{self.player_name}\'s First Utterance: {completion1.choices[0].message.content}', json_file)
            json.dump(f'{self.player_name}\'s Second Utterance: {completion2.choices[0].message.content}', json_file)
            json_file.write('\n')
        return completion2.choices[0].message.content

class Summarizer:

    def __init__(self, openai_api_key, max_tokens, role):
        self.role=role
        self.summary=''
        self.memory=[]
        self.client=OpenAI(api_key=openai_api_key)
        self.max_tokens=max_tokens
        self.player_name='summarizer'

    def append_memory(self, role, memory_item):
        self.memory.append({'role':role, 'content':memory_item})

    def summarize(self):
        #TODO
        prompt=[{'role':'system', 'content': f"{str(self.memory)}\nYou are a summarizer, not a player. This is a record given to a {self.role} player in a mafia game. Organize history around unusual points and suggest an appropriate strategy for {self.role} player(within 100 tokens total)."}]
        completion = self.client.chat.completions.create(model='gpt-4o-mini', temperature=0.5, messages=prompt, max_completion_tokens=200)
        print(completion.choices[0].message.content)
        return completion.choices[0].message.content

class Game:

    def __init__(self, openai_api_key, max_tokens, player_count, discussion_depth, use_gpt4, render_markdown, num_mafia=2, num_citizen=3, doctor=True, police=True, output=None):
        self.client=OpenAI(api_key=openai_api_key)
        self.max_tokens=max_tokens
        self.num_mafia=num_mafia ##11/12 준하
        self.num_citizen=num_citizen ##11/12 준하
        self.num_doctor=int(doctor) ##11/12 준하
        self.num_police=int(police) ##11/12 준하
        self.num_villagers=self.num_citizen+self.num_doctor+self.num_police
        self.player_count = num_mafia+self.num_villagers ##11/12 준하
        self.discussion_depth = discussion_depth
        self.card_list = None
        self.player_names = []
        self.players = []
        self.use_gpt4 = use_gpt4
        self.mafia_id = [] ## 11/11 경현
        self.summarizers={'mafia':Summarizer(openai_api_key,max_tokens,'mafia'), 'police':Summarizer(openai_api_key,max_tokens,'police'),'doctor':Summarizer(openai_api_key,max_tokens,'doctor'),'citizen':Summarizer(openai_api_key,max_tokens,'citizen')}
        self.history=[]
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        self.file_name = f"record_project_{timestamp}.json"
        

        if render_markdown:
            self.rendering_engine = MarkdownRenderingEngine()
        else:
            self.rendering_engine = ConsoleRenderingEngine()
        
        self.players.append(Player(self.client, self.max_tokens, input("Insert your name : "), 0, False, self.file_name, user=True))##11/12 준하
        agent_names=self.get_player_names(self.player_count-1, [self.players[0].player_name])
        for i in range(len(agent_names)):
            self.players.append(Player(self.client, self.max_tokens, agent_names[i],i+1,self.use_gpt4, self.file_name))
        for player in self.players:
            self.player_names.append(player.player_name)
        self.players_summarizers=self.players+list(self.summarizers.values())
        print("--------summarizers start----------") ### 11/27 경현
        print(self.players_summarizers)
        print("--------summarizers End----------") ### 11/27 경현
        #user와 agent 설정은 여기서



    def play(self):
        """one turn of the game (게임 소개 -> 밤 -> 낮 -> 투표)
        게임
        """
        # 게임 초기화: 맨 첫번쨰 turn에만 필요할 것 같음
        self.initialize_game()
        # 게임 소개: 맨 첫번째 turn에만 필요할 것 같음
        #self.rendering_engine.render_system_message(open('intro.txt').read().strip(), no_wait=True)
        self.introduce_players()
        day=1
        self.first_day()
        
        while True:
        # 게임 시작
        # 1. 밤부터 시작            

            self.rendering_engine.render_phase('NIGHT'+str(day))
            self.append_players_memory('system','Night'+str(day)+' start',self.players_summarizers)
            #   플레이어 순서대로 행동
            mafia_target=self.night_mafia(day)
            print('Mafia Done')
            doctor_save=self.night_doctor(day)
            print('Doctor Done')
            self.night_police(day)
            print('Police Done')

            day+=1

            # 2. 낮
            self.rendering_engine.render_phase('DAY'+str(day))
            self.append_players_memory('system','Day'+str(day)+' start',self.players_summarizers)
            self.check_dead(mafia_target,doctor_save,day)
            end, end_text=self.check_condition()
            if end:
                print(end_text)
                break
            self.day() # 토론
            
            # 3. 투표
            self.rendering_engine.render_phase('VOTE')
            self.vote(day)
            end, end_text=self.check_condition()
            if end:
                print(end_text)
                break
            
        # 4. 게임 종료 및 현황 정리
        #self.rendering_engine.render_game_details(self.player_count, self.discussion_depth, self.use_gpt4)


    def initialize_game(self):
        # player instance 생성 - 이름, 번호, 역할 부여
        '''role_list = ['mafia', 'mafia', 'doctor', 'police', 'citizen', 'citizen'] ## 11/11 경현
        numbers = list(range(1, self.player_count + 1)) ## 11/11 경현
        random.shuffle(numbers) ## 11/11 경현
        self.player_names = self.get_player_names(self.player_count)
        
        self.players = [Player(self.player_names[i], i+1, role_list[numbers[i]], True) for i in range(self.player_count)] ## 11/11 경현
        self.mafia_id = [player.player_number for player in self.players if player.role == 'mafia'] ## 11/11 경현'''
        ##11/12 준하
        role_list = ['mafia' for _ in range(self.num_mafia)]+['doctor' for _ in range(self.num_doctor)]+['police' for _ in range(self.num_police)]+['citizen' for _ in range(self.num_citizen)]
        self.mafia_id=[]
        random.shuffle(role_list)
        for i in range(self.player_count):
            if role_list[i] == 'mafia':
                self.mafia_id.append(i)
            self.players[i].role=role_list[i]
            self.players[i].summarizer=self.summarizers[role_list[i]]
        print("System: Players are"+str(self.player_names))
        self.append_players_memory('system','Players are'+str(self.player_names),self.players_summarizers)
        # Rule Prompt TODO


        # Tip Prompt TODO


    def introduce_players(self):
        ## 11/11 경현 추가
        """본인의 role 소개 및 마피아 간에 서로 확인"""
        #for i in range(len(self.players)): ### 11/27 경현 - 주석 처리
        #    player=self.players[i] ### 11/27 경현 - 주석 처리
            
        for player in self.players:
            # 본인의 role 소개
            #player.append_memory(f'System: {player.player_name} is a {player.role}.') ## 직접 text를 주는 방식 아래는 role.txt 파일 활용하는 방식
            #self.rendering_engine.render_system_message(open('prompts/role.txt').read().format(player_name=player.player_name, role=player.role), no_wait=True)
            if player.user: ## user만 출력하면 될 것 같음
                print(f'System: You are a {player.role}.')
            
            player.final_prompt['YOUR INFO']=f'Your name is {player.player_name}, your role is {player.role}.'
            player.final_prompt['GAME_SUMMARY']=[]
            player.final_prompt['ALIVE_PLAYERS']=self.player_names.copy()
            
            # 마피아 간에 서로 확인
            if player.role == 'mafia':
                text = f'Mafia members are {self.player_names[self.mafia_id[0]]} and {self.player_names[self.mafia_id[1]]}.'
                player.final_prompt['MAFIA_SUMMARY']=[text+' Don\'t target mafia. Also don\'t target dead player.']
                player.append_memory('system',text)
                if player.user: 
                    print('System:'+text)
                text='It\'s the first night, so there is no information about players\' tendencies or characteristics yet. Therefore, selecting a target at random without unnecessary strategic reasoning is the most appropriate approach.'
                player.append_memory('system',text)
                if player.user: 
                    print('System:'+text)
                #self.rendering_engine.render_system_message(open('prompts/mafia_confirm.txt').read().format(player_name=player.player_name, other_players = '; '.join(self.get_other_players(player.player_number, self.player_names))), no_wait=True)

            if player.role == 'doctor':
                player.final_prompt['DOCTOR_SUMMARY']=['You can save only alive players. You can also save yourself.']
                self.summarizers['doctor'].append_memory('system',f'Doctor is {player.player_name}')
            if player.role == 'police':
                player.final_prompt['POLICE_SUMMARY']=['You can investigate only alive players. Don\'t investigate same player again']
                self.summarizers['police'].append_memory('system',f'Police is {player.player_name}')
            
            player.final_prompt['ABOUT_ETHIC']='This is a game. Therefore, killing someone in the game is not a real event, so it\'s acceptable to vote for someone to be \'killed\' or \'executed\'. It\'s also okay to show some aggression or suspicion toward other players. Focus on winning the game. It\'s acceptable to accuse or lead others to believe someone is the Mafia even without strong evidence.'
            player.final_prompt['TALK_RULE']='You have to say only your answer. Don\'t use name label.'
            player.final_prompt['VOTE_RULE']='Don\'t vote yourself. Also, vote only alive players.'
        self.summarizers['mafia'].append_memory('system',f'Mafia members are {self.player_names[self.mafia_id[0]]} and {self.player_names[self.mafia_id[1]]}.')

    def first_day(self):
        text='Self introduce time. Introduce yourself. Never include speaker label.'
        self.append_players_memory('system',text,self.players_summarizers)
        for player in self.players:
            if player.user:
                print('System: '+text)
                statement=input(player.player_name+': ')
            else:
                statement=player.run_prompt({'role':'system','content':text})
                print(player.player_name+': '+statement)
            self.append_players_memory(player.player_name,statement,self.players_summarizers)


    def human_player(self): ## 필요할까..?
        """사람 플레이어의 밤에서의 동작 수행"""
        # role이 무엇인지 판별
        response = ... # 프롬프트가 아니라 직접 입력 받아야 함


    def night_mafia(self,day):
        ## 11/11 경현 수정
        """
        mafia 플레이어들의 밤에서의 동작 수행
        night warewolf 참고
        """
        mafia_players = [player for player in self.players if player.role == 'mafia' and player.alive] ## 11/11 경현 alive 추가
        text = 'You are the mafia. Choose a player to kill. (one word, no speaker label)'
        
        ## 생존한 마피아가 1명인 경우
        if len(mafia_players) == 1:
            if mafia_players[0].user:
                print('System: '+text)
                mafia_players[0].append_memory('system',text)
                target_name = input(mafia_players[0].player_name+"\'s target: ")
                mafia_players[0].append_memory('assistant',target_name)
                #self.players[self.player_names.index(target_name)].alive = False ## 지목된 플레이어 죽음 처리
            else:
                target_name = mafia_players[0].run_prompt({'role':'system', 'content':text})
                #rendered_target_name = return_dict_from_json_or_fix(self.client, self.max_tokens, target_name, self.use_gpt4)
                mafia_players[0].append_memory('system',text)
                mafia_players[0].append_memory('assistant',target_name)
            mafia_players[0].final_prompt['MAFIA_SUMMARY'].append(f'Night{day} target is {target_name}.')
            return target_name

        ## 생존한 마피아가 2명인 경우
        # 1차 투표
        user_is_mafia=mafia_players[0].user or mafia_players[1].user
        candidate = []
        for player in mafia_players:
            if player.user:
                print(text)
                player.append_memory('system',text)
                response = input(player.player_name+"\'s target: ")
                player.append_memory('assistant',response)
                candidate.append(response)
            else:
                response = player.run_prompt({'role':'system', 'content':text})
                candidate.append(response)
                #rendered_response = return_dict_from_json_or_fix(self.client, self.max_tokens, response, self.use_gpt4)
                player.append_memory('system',text)
                player.append_memory('assistant',response)
        vote_result=mafia_players[0].player_name+" selected "+candidate[0]+', '+mafia_players[1].player_name+" selected "+candidate[1]
        for player in mafia_players:
            player.final_prompt['MAFIA_SUMMARY'].append(f'Night {day} first vote result : {vote_result}')
        if user_is_mafia:
            print(vote_result)
        self.append_players_memory('system', vote_result, mafia_players)
        self.summarizers['mafia'].append_memory('system',vote_result)

        ## 1차 투표 결과 확인
        if candidate[0] == candidate[1]: ## 1차 투표 결과가 같은 경우
            target_name = candidate[0]
            #self.players[self.player_names.index(target_name)].alive = False
            for player in mafia_players:
                player.final_prompt['MAFIA_SUMMARY'].append(f'Night{day} target is {target_name}.')
            return target_name
        
        ## 1차 투표 결과가 다른 경우
        ## 토론 TODO
        if user_is_mafia:
            print("System: Two mafia select other target. Debate with other mafia about selecting target. If debate ends, please remain silent until instructed by the system.")
        self.append_players_memory("system", "Two mafia select other target. Debate with other mafia about selecting target. If debate ends, please remain silent until instructed by the system.",mafia_players+[self.summarizers['mafia']])
        i=random.randint(0,1)
        for _ in range(10):
            statement=mafia_players[i].run_prompt({'role':'system','content':'No speaker label'})
            if user_is_mafia and not mafia_players[i].user:
                print(mafia_players[i].player_name+": "+statement)
            self.append_players_memory(mafia_players[i].player_name,statement,mafia_players+[self.summarizers['mafia']])
            i=1-i

        ## 2차 투표
        candidate = []
        for player in mafia_players:
            if player.user:
                print(text)
                player.append_memory('system',text)
                response = input(player.player_name+"\'s target: ")
                player.append_memory('assistant',response)
                candidate.append(response)
            else:
                response = player.run_prompt({'role':'system', 'content':text})
                candidate.append(response)
                #rendered_response = return_dict_from_json_or_fix(self.client, self.max_tokens, response, self.use_gpt4)
                player.append_memory('system',text)
                player.append_memory('assistant',response)
        vote_result=mafia_players[0].player_name+" selected "+candidate[0]+', '+mafia_players[1].player_name+" selected "+candidate[1]
        for player in mafia_players:
            player.final_prompt['MAFIA_SUMMARY'].append(f'Night {day} final vote result : {vote_result}')
        if user_is_mafia:
            print(vote_result)
        self.append_players_memory('system', vote_result, mafia_players+[self.summarizers['mafia']])

        ## 2차 투표 결과 확인
        if candidate[0] == candidate[1]: ## 2차 투표 결과가 같은 경우
            target_name = candidate[0]
            #self.players[self.player_names.index(target_name)].alive = False
            for player in mafia_players:
                player.final_prompt['MAFIA_SUMMARY'].append(f'Night{day} target is {target_name}.')
            return target_name
        else: ## 2차 투표 결과가 다른 경우 - 두 후보 중 랜덤으로 선택
            target_name = random.choice(candidate)
            #self.players[self.player_names.index(target_name)].alive = False
            for player in mafia_players:
                player.final_prompt['MAFIA_SUMMARY'].append(f'Night{day} target is {target_name}.')
            return target_name
        

        
    def night_doctor(self,day):##11/12 준하
        """
        의사 플레이어들의 밤에서의 동작 수행
        의사는 밤에 한 명을 지목하여 치료한다.
        """
        text = 'You are the doctor. Please select a player to save.(one word, no speaker label)'
        doctor_players = [player for player in self.players if player.role == 'doctor' and player.alive]
        if len(doctor_players)==1:
            player=doctor_players[0]
            if player.user:
                print('System: '+text)
                target_name=input("Player name: ")
            else:
                target_name = player.run_prompt({'role':'system','content':text})
            player.append_memory('system',text)
            player.append_memory('assistant',target_name)
            #self.players[self.player_names.index(target_name)].alive = True
            player.final_prompt['DOCTOR_SUMMARY'].append(f'Night{day}, You saved {target_name}')
            self.summarizers['doctor'].append_memory('system',f'Night{day}, You saved {target_name}')
            return target_name
        
    def night_police(self,day):##11/12 준하
        """ 
        경찰 플레이어들의 밤에서의 동작 수행
        """
        text = 'Choose a player to check if he or she is a mafia or a citizen.(one word, no speaker label)'
        police_players = [player for player in self.players if player.role == 'police' and player.alive]
        if len(police_players)==1:
            player=police_players[0]
            if player.user:
                print('System: '+text)
                target_name=input("Player name: ")
            else:
                target_name = player.run_prompt({'role':'system','content':text})
            player.append_memory('system',text)
            player.append_memory('assistant',target_name)
            target_player=self.players[self.player_names.index(target_name)]
            output_text = target_name+' is '+('mafia' if target_player.role=='mafia' else 'not mafia')
            if player.user:
                print(output_text)
            player.append_memory('system',output_text)
            player.final_prompt['POLICE_SUMMARY'].append(f'Night{day}, you investigate {target_name}, {output_text}')
            self.summarizers['police'].append_memory('system',f'Night{day}, you investigate {target_name}, {output_text}')
        
    def check_dead(self, mafia_target, doctor_save,day):
        if mafia_target==doctor_save:
            text=f'Mafia shot {mafia_target}, but doctor save {mafia_target}!'
        else:
            text=f'{mafia_target} dead.'
            self.players[self.player_names.index(mafia_target)].alive = False
            for player in self.players:
                player.final_prompt['ALIVE_PLAYERS'].remove(mafia_target)
        print('System: '+text)
        self.append_players_memory('system', text, self.players_summarizers)
        for player in self.players:
            player.final_prompt['GAME_SUMMARY'].append(f'Night{day} : {text}')
        

    def day(self):##11/13 준하
        """낮에는 모든 플레이어가 토론을 한다. 토론이 끝나면 투표를 진행한다."""
        '''self.rendering_engine.render_game_statement('It is now daytime. Time for discussion.')
        day_prompt = open('prompts/day.txt').read()'''

        '''### 토론 시작
        # num_utterance = 0
        radom_start = random.randint(0, len(self.players) - 1) # 랜덤으로 토론을 시작하는 플레이어를 정함
        for player in self.players: # TODO: 이 부분을 pointing 방식로 바꿔야 할 것 같음
            # if num_utterance >= self.discussion_depth: break
            # num_utterance += 1
            self.rendering_engine.render_player_turn_init(player)

            response = player.run_prompt(day_prompt)

            action = return_dict_from_json_or_fix(response, self.use_gpt4)
            reasoning = action['reasoning']
            statement = action['statement']

            self.rendering_engine.render_player_turn(player, statement, reasoning)

        self.rendering_engine.render_system_message('Discussion has ended.', ref_players=self.players, ref_cards=[player.card for player in self.players])'''

        ### 토론 내용 정리
        players_alive=[player for player in self.players if player.alive]
        print('System: It is now daytime. Time for discussion.')
        self.append_players_memory('system', 'It is now daytime. Time for discussion.',self.players_summarizers)
        talk_player = players_alive[random.randint(int(self.players[0].alive),len(players_alive)-1)]
        next_talk_player = talk_player
        for _ in range(10):
            if self.players[0].alive and (not talk_player.user) and (not next_talk_player.user) and input("Will you talk?(y/n): ")=='y':
                next_talk_player=self.players[0]
            talk_player=next_talk_player
            if talk_player.user:
                statement=input(talk_player.player_name+': ')
                #talk_player.append_memory(talk_player.player_name+": "+statement)
                self.append_players_memory(talk_player.player_name,statement,self.players_summarizers)
                print(self.players[1].memory[-1])
                next_player_name=input('Choose the next player to talk to except you: ')
            else:
                statement=talk_player.run_prompt({'role':'system','content':'Say only your statement. Never include speaker label.'})
                #talk_player.append_memory(talk_player.player_name+": "+statement)
                self.append_players_memory(talk_player.player_name,statement,self.players_summarizers)
                next_player_name=talk_player.run_prompt({'role':'system','content':'Choose the next player to talk to except you. One word, no speaker label'}, summarize=False)
                print(talk_player.player_name+': '+statement)
            if next_player_name in self.player_names:
                next_talk_player=self.players[self.player_names.index(next_player_name)]
                if not next_talk_player.alive:
                    next_talk_player=players_alive[random.randint(self.players[0].alive,len(players_alive)-1)]
            else:
                next_talk_player=players_alive[random.randint(self.players[0].alive,len(players_alive)-1)]

        
    def vote(self,day):##11/13 준하
        """토론 진행"""
        '''self.rendering_engine.render_game_statement('It\'s time to vote!')
        vote_prompt = open('prompts/vote.txt').read()'''

        
        players_alive=[player for player in self.players if player.alive]
        #투표
        print('System: It\'s time to vote!')
        self.append_players_memory('system','It\'s time to vote!',players_alive)
        while True:
            votes = {player.player_name : [] for player in players_alive}
            for player in players_alive:
                if player.user:
                    pointed=input('Vote: ')
                else:
                    pointed=player.run_prompt({'role':'system','content':'Say only suspect\'s name. No speaker label'})
                player.append_memory('system', 'Vote for suspect.')
                player.append_memory('assistant', pointed)
                if pointed in votes:
                    votes[pointed].append(player.player_name)
            max_vote_count = max([len(count) for count in votes.values()])
            max_voters = [name for name, count in votes.items() if len(count) == max_vote_count]
            print('System: Vote result is'+str(votes))
            self.append_players_memory('system','Vote result is'+str(votes),self.players_summarizers)
            if len(max_voters)==1:
                break
            print("System: There are multiple candidates with the highest votes, so we will proceed with a revote.")
            self.append_players_memory('system', 'There are multiple candidates with the highest votes, so we will proceed with a revote.',self.players_summarizers)
        suspect=self.players[self.player_names.index(max_voters[0])]
        #최후의 변론
        print("System: The suspect will now have the opportunity for a final statement.")
        self.append_players_memory('system','The suspect will now have the opportunity for a final statement.',self.players_summarizers)
        statement=suspect.run_prompt({'role':'system','content':'You are suspect! Make your final statement.'})
        self.append_players_memory(suspect.player_name,statement,self.players_summarizers)
        print(statement)
        #최종투표
        print('System: It\'s time for final vote!')
        self.append_players_memory('system', 'It\'s time for final vote!',self.players_summarizers)
        final_vote={'y':[],'n':[]}
        yes_count=0
        for player in players_alive:
            if player==suspect:
                continue
            if player.user:
                response=input('Execute suspect?(y/n): ')
            else:
                response=player.run_prompt({'role':'system','content':'Kill?(y/n)'})
            player.append_memory('system', 'Execute suspect?(y/n)')
            player.append_memory('assistant', response)
            if response in final_vote:
                final_vote[response].append(player.player_name)
            yes_count+=(response=='y')
        final_vote_result='Final result is '+str(final_vote)+'.\n'
        if 2*yes_count>len(players_alive)-1:
            suspect.alive=False
            for player in self.players:
                player.final_prompt['ALIVE_PLAYERS'].remove(suspect.player_name)
            final_vote_result+=f'{suspect.player_name} executed!'
            if suspect.role=='mafia':
                final_vote_result+=f'{suspect.player_name} was mafia!'
            else:
                final_vote_result+=f'{suspect.player_name} was a citizen!'
        else:
            final_vote_result+=f'{suspect.player_name} not excuted!'
        print('System: '+final_vote_result)
        self.append_players_memory('system', final_vote_result, self.players_summarizers)
        for player in self.players:
            player.final_prompt['GAME_SUMMARY'].append(f'Day{day} vote result : {final_vote_result}')

    
    def check_condition(self): ##11/12 준하
        """게임종료여부 확인"""
        alive_count=0
        mafia_count=0
        for player in self.players:
            alive_count+=player.alive
            mafia_count+=(player.alive and player.role=='mafia')
        if mafia_count==0:
            return True, "Villagers win!"
        if alive_count/2<=mafia_count:
            return True, "Mafia win!"
        return False, None

    def get_player_names(self, player_count, exclude_names=None):##11/12 준하 수정(user name 중복 안되게)
        """역할별 이름 부여"""
        name_options = ['Alexandra', 'Alexia', 'Andrei', 'Cristina', 'Dragos', 'Dracula', 'Emil', 'Ileana', 'Kraven', 'Larisa', 'Lucian', 'Marius', 'Michael', 'Mircea', 'Radu', 'Semira', 'Selene', 'Stefan', 'Viktor', 'Vladimir']
        if exclude_names:
            name_options = [name for name in name_options if name not in exclude_names]
        return random.sample(name_options, player_count)

    def get_other_players(self, player_number, player_names):
        """남아있는 플레이어 이름을 반환"""
        return [name for i, name in enumerate(player_names, 1) if i != player_number]
    
    def append_players_memory(self, name, memory_item, players):#한 번에 메모리 추가
        role=None
        content=memory_item
        if name=='system':
            with open(self.file_name, 'a') as json_file:
                json.dump(f'{name} : {content}', json_file)
                json_file.write('\n')        
        for player in players:
            if name=='system':
                role='system'
            elif name==player.player_name:
                role='assistant'
            else:
                role='user'
                content=name+': '+content
            player.append_memory(role, content)


### Helper functions ###

def return_dict_from_json_or_fix(client, max_tokens, message_json, use_gpt4):
    """
    Json으로 적은 메시지 딕셔너리를 챗 지피티를 통해 검증하는 코드
    If the data is valid json, return it as a dictionary, if not, it will attempt to use AI to intelligently fix the JSON.
    If that still does not work, it will print the original (bad) JSON, the new bad JSON, and then exit gracefully.

    This totally badass code came from Yosef Frost: https://github.com/FrostyTheSouthernSnowman
    """

    model = 'gpt-3.5-turbo' if not use_gpt4 else 'gpt-4'

    try:
        message_dict = json.loads(message_json)

    except ValueError:
        completion = client.chat.completions.create(model=model, temperature=0.8, messages=[
            {
                'role': 'user', 
                'content': 'I have a JSON string, but it is not valid JSON. Possibly, the message contains other text besides just the JSON. Could you make it valid? Or, ' \
                + 'if there is valid JSON in the response, please just extact the JSON and do NOT update it. Please respond ONLY in valid JSON! Do not comment on your response. Do not start or ' \
                + 'end with backpacks ("`" or "```")!  You must ONLY respond in JSON! Anything after the colon is JSON I need you to fix. The original message that contains the ' \
                + f'bad JSON is: \n {message_json}'
            }], max_completion_tokens=max_tokens)
        fixed_json = completion.choices[0].message.content
        try:
            message_dict = json.loads(fixed_json)

        except ValueError:
            print('Unable to get valid JSON response from GPT. Exiting program gracefully.')
            print(f'Debug info:\n\tOriginal Response: {message_json}\n\tAttempted Fix: {fixed_json}')
            exit(1)

    return message_dict['message']

class ConsoleRenderingEngine:

    player_colors = [Fore.YELLOW, Fore.GREEN, Fore.BLUE, Fore.MAGENTA, Fore.CYAN]

    def __init__(self):
        pass

    def get_player_colored_name(self, player):
        return f'{self.player_colors[player.player_number - 1]}{Style.BRIGHT}{player.player_name}{Style.RESET_ALL}'

    def type_line(self, text):
        for char in text:
            print(char, end='', flush=True)
            #time.sleep(random.uniform(0.005, 0.015)) ### 11/27 경현
        print()

    def render_system_message(self, statement, ref_players=[], ref_cards=[], no_wait=False):
        print()
        ref_players_formatted = []
        for player in ref_players:
            ref_players_formatted.append(self.get_player_colored_name(player))
        ref_cards_formatted = []
        for card in ref_cards:
            ref_cards_formatted.append(f'{Fore.RED}{Style.BRIGHT}{card}{Style.RESET_ALL}')
        print(statement.format(ref_players = ref_players_formatted, ref_cards = ref_cards_formatted));
        #if not no_wait: ### 11/27 경현
            #time.sleep(random.uniform(1, 3)) ### 11/27 경현

    def render_phase(self, phase):
        print()
        print(f'=== The {Fore.RED}{Style.BRIGHT}{phase}{Style.RESET_ALL} phase will now commence. ===')

    def render_game_statement(self, statement):
        print()
        print(f'{Fore.WHITE}{Style.BRIGHT}GAME{Style.RESET_ALL}: ', end='')
        self.type_line(statement)
        #time.sleep(random.uniform(1, 3)) ### 11/27 경현
        
    def render_player_turn_init(self, player):
        print()
        player_colored_name = self.get_player_colored_name(player)
        print(f'{player_colored_name} (thoughts as {player.card_thought}): ', end='', flush=True)

    def render_player_turn(self, player, statement, reasoning):
        player_colored_name = self.get_player_colored_name(player)
        self.type_line(reasoning)
        #time.sleep(random.uniform(1, 3)) ### 11/27 경현
        if statement is not None:
            print(f'{player_colored_name}: ', end='')
            self.type_line(statement)

    def render_player_vote(self, player, voted_player, reasoning):
        player_colored_name = self.get_player_colored_name(player)
        self.type_line(reasoning)
        #time.sleep(random.uniform(1, 3)) ### 11/27 경현
        print(f'{player_colored_name} [{player.display_card}]: ', end='')
        self.type_line(f'I am voting for {voted_player}.')

    def render_vote_results(self, votes, players):
        print()
        print('The votes were:')
        print()
        for player in players:
            if votes[player.player_name] > 0:
                print(f'{player.player_name} : {player.card} : {votes[player.player_name]}')

    def render_game_details(self, player_count, discussion_depth, use_gpt4):
        model = 'gpt-3.5-turbo' if not use_gpt4 else 'gpt-4'

        print()
        print('## Run Details')
        print()
        print(f'* Model: {model}')
        print(f'* Player Count: {player_count}')
        print(f'* Discussion Depth: {discussion_depth}')
        print()

class MarkdownRenderingEngine:

    def __init__(self):
        print('# Werewolf GPT - Recorded Play')

    def render_system_message(self, statement, ref_players=[], ref_cards=[], no_wait=False):
        print()
        ref_players_formatted = []
        for player in ref_players:
            ref_players_formatted.append(f'**{player.player_name}**')
        ref_cards_formatted = []
        for card in ref_cards:
            ref_cards_formatted.append(f'***{card}***')
        print(statement.format(ref_players = ref_players_formatted, ref_cards = ref_cards_formatted));

    def render_phase(self, phase):
        print()
        print('---')
        print()
        print(f'## The ***{phase}*** phase will now commence.')

    def render_game_statement(self, statement, ref_players=[], ref_cards=[]):
        print()
        print(f'>***GAME:*** {statement}')

    def render_player_turn_init(self, player):
        # Markdown rendering doesn't need to do anything here. This method is called when
        # an AI begins to think of it's actions.
        pass

    def render_player_turn(self, player, statement, reasoning):
        print()
        print(f'***{player.player_name} (thoughts as {player.card_thought}):*** {reasoning}')
        if statement is not None:
            print(f'> **{player.player_name}:** {statement}')

    def render_player_vote(self, player, voted_player, reasoning):
        print()
        print(f'***{player.player_name} (thoughts as {player.card_thought}):*** {reasoning}')
        print(f'> **{player.player_name} [{player.display_card}]:** I am voting for {voted_player}.')

    def render_vote_results(self, votes, players):
        print()
        print('The votes were:')
        print()
        for player in players:
            if votes[player.player_name] > 0:
                print(f'* {player.player_name} : {player.card} : {votes[player.player_name]}')

    def render_game_details(self, player_count, discussion_depth, use_gpt4):
        model = 'gpt-3.5-turbo' if not use_gpt4 else 'gpt-4'

        print()
        print('## Run Details')
        print()
        print(f'* Model: {model}')
        print(f'* Player Count: {player_count}')
        print(f'* Discussion Depth: {discussion_depth}')





#game = Game(player_count = 5, discussion_depth = 20, use_gpt4 = True    , render_markdown = False)
#game.play()

@click.command()
@click.option('--player-count', type=int, default=5, help='Number of players')
@click.option('--discussion-depth', type=int, default=20, help='Number of discussion rounds')
@click.option('--use-gpt4', is_flag=True, default=False, help='Use GPT-4 for discussion')
@click.option('--render-markdown', is_flag=True, default=False, help='Render output as markdown')
def play_game(player_count, discussion_depth, use_gpt4, render_markdown):
    game = Game(openai_api_key=open_api_key, max_tokens=100, player_count=player_count, discussion_depth=discussion_depth, use_gpt4=use_gpt4, render_markdown=render_markdown)
    game.play()

if __name__ == '__main__':
    play_game()
