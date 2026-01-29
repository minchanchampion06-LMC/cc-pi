import pygame
import asyncio
import random
import math
import sys

# 1. 초기 설정

pygame.init()
pygame.mixer.init()
try:
    kill_sound = pygame.mixer.Sound("fat.io/kill_sound.mp3")
    kill_sound.set_volume(1.0) # 볼륨 조절 (0.0 ~ 1.0)
except:
    kill_sound = None
    print("효과음 파일을 찾을 수 없습니다.")
SCREEN_WIDTH, SCREEN_HEIGHT = 1900, 1000
MAP_WIDTH, MAP_HEIGHT = 9000, 4000
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("FAT.io")
clock = pygame.time.Clock()


# 2. 10단계 캐릭터

TIER_DATA = [
    {"tier": 1, "radius": 30, "speed": 4.0, "rotation_speed": 0.18, "color": (160, 140, 120), "img_name": "mouse.png","body_ratio": 0.75, "offset": (0, 0)},  # 쥐
    {"tier": 2, "radius": 80, "speed": 3.3, "rotation_speed": 0.12, "color": (230, 230, 200), "img_name": "pig.png","body_ratio": 0.88, "offset": (0, 0)},  # 돼지
    {"tier": 3, "radius": 68, "speed": 3.1, "rotation_speed": 0.11, "color": (255, 180, 200),"img_name": "gray pig.png", "body_ratio": 0.65, "offset": (0, 0)},  # 멧돼지
    {"tier": 4, "radius": 72, "speed": 3.1, "rotation_speed": 0.15, "color": (100, 200, 100), "img_name": "wolf.png","body_ratio": 0.65, "offset": (0, 0)},  # 늑대
    {"tier": 5, "radius": 95, "speed": 3.1, "rotation_speed": 0.15, "color": (150, 150, 150), "img_name": "bear.png","body_ratio": 0.85, "offset": (0, 0)},  # 곰
    {"tier": 6, "radius": 98, "speed": 3.1, "rotation_speed": 0.15, "color": (255, 140, 0), "img_name": "elephant.png","body_ratio": 0.55, "offset": (0, 0)},  # 코끼리
    {"tier": 7, "radius": 90, "speed": 3.1, "rotation_speed": 0.13, "color": (139, 69, 19), "img_name": "dragon.png","body_ratio": 0.60, "offset": (0, 0)},  # 청룡
    {"tier": 8, "radius": 105, "speed": 3.1, "rotation_speed": 0.13, "color": (50, 50, 50),"img_name": "landmonster.png", "body_ratio": 0.36, "offset": (30, 0)},  # 랜드몬스터
    {"tier": 9,  "radius": 120, "speed": 3.3, "rotation_speed": 0.15, "color": (0, 100, 255),"img_name": "BD.png", "body_ratio": 0.3, "offset": (-90, 7)},   # BD
    {"tier": 10, "radius": 120, "speed": 3.5, "rotation_speed": 0.16, "color": (255, 0, 0),"img_name": "KD.png", "body_ratio": 0.3, "offset": (-122, 0)}     # KD
]


# 3. 플레이어, 봇의 기본 속성

class Entity:
    def __init__(self, x, y, tier_idx, is_bot=True):
        self.x, self.y = x, y
        self.is_bot = is_bot
        if not is_bot:
            self.name = "YOU"
        else:
            self.name = f"Bot-{random.randint(100,999)}"
        self.xp = 0 # 현재 경험치
        self.hp = 100
        self.max_hp = 100
        self.update_stats(tier_idx) # 여기서 색상까지 업데이트함
        self.angle = random.uniform(0, math.pi * 2)
        self.angle = 0
        self.last_attack_time = 0
        self.view_range = 400
        self.knockback_speed = 0  # 현재 밀려나고 있는 속도
        self.knockback_angle = 0  # 밀려나는 방향
        self.energy = 100  # 대시 에너지 (최대 100)
        self.is_dashing = False
        self.dash_multiplier = 3.0  # 대시 시 속도 배율 (2배)
        self.last_ai_update = 0  # 마지막으로 AI 결정을 내린 시간
        self.ai_interval = random.randint(1500, 3000)  # 결정 유지 시간 (1.5초~2.0초)
        self.current_decision = "wander"  # 현재 수행 중인 행동 상태
        self.target_coords = (x, y)  # 이동 목표 지점
        self.angle = random.uniform(0, math.pi * 2)  # 현재 바라보는 각도
        self.stun_timer = 0  # 0보다 크면 입력 무시 (단위: 밀리초)



    def update_stats(self, idx):
        idx = min(idx, 9)
        data = TIER_DATA[idx]
        self.tier_idx = idx
        self.tier = data["tier"]
        self.radius = data["radius"]
        self.speed = data["speed"]
        self.color = data["color"] # 단계별 고정 색상 적용!
        self.base_speed = TIER_DATA[idx]["speed"]
        self.speed = self.base_speed
        self.rotation_speed = data["rotation_speed"]
        if self.is_bot:
            self.rotation_speed *= 0.75
        self.max_hp = 100 + (20 * idx)
        self.hp = self.max_hp
        self.max_xp = 100 * (2 ** idx)
        if self.tier_idx == 0:
            self.before_xp = 0
        else:
            self.before_xp = 100 * (2 ** (idx - 1))
        self.body_ratio = data.get("body_ratio", 1.0)  # 기본값은 1.0 (이미지 전체가 몸통일 때)
        self.offset = data.get("offset") # 오프셋 정보 가져오기

        try:
            raw_img = pygame.image.load(f"fat.io/{data['img_name']}").convert_alpha()

            # [핵심 계산]
            # 몸통 지름(radius * 2)이 이미지 내에서 body_ratio만큼의 비중을 가져야 하므로
            # 전체 이미지의 크기는 (지름 / 비율) 이 되어야 합니다.
            display_size = int((self.radius * 2) / self.body_ratio)

            self.image = pygame.transform.scale(raw_img, (display_size, display_size))
        except:
            self.image = None

        # 부활/진화 시 현재 경험치를 해당 티어의 시작 경험치로 맞춤
        self.xp = self.before_xp



    def gain_xp(self, amount):
        self.xp += amount
        # 경험치가 꽉 찼고, 아직 최고 단계가 아니라면 진화!
        if self.xp >= self.max_xp and self.tier_idx < 9:
            self.update_stats(self.tier_idx + 1)
            self.hp = self.max_hp
            self.xp = self.before_xp
            print(f"{'봇' if self.is_bot else '플레이어'}가 {self.tier}단계로 진화했습니다!")

    def update_energy(self):
        """에너지 소모 및 회복 로직"""
        if self.is_dashing and self.energy > 0:
            self.speed = self.base_speed * self.dash_multiplier
            self.energy -= 1  # 대시 중 에너지 소모 속도
            if self.energy <= 0:
                self.energy = 0
                self.is_dashing = False
        else:
            self.speed = self.base_speed
            if self.energy < 100:
                self.energy += 0.1  # 가만히 있거나 걸을 때 에너지 회복



    def update_stun(self):
        if self.stun_timer > 0:
            self.stun_timer -= 1000 // 60
            if self.stun_timer < 0:
                self.stun_timer = 0

    def update_knockback(self):
        """매 프레임 호출되어 넉백 효과를 감쇠시키며 이동함"""
        if 0 < self.knockback_speed:
            # 설정된 방향으로 밀려남
            self.x += math.cos(self.knockback_angle) * self.knockback_speed
            self.y += math.sin(self.knockback_angle) * self.knockback_speed
            self.knockback_speed *= 0.9
        else:
            self.knockback_speed = 0

    def move_towards(self, tx, ty, reverse=False):
        if self.stun_timer > 0:
            return
        dx, dy = tx - self.x, ty - self.y
        dist = math.hypot(dx, dy)

        if dist > 2:
            # 1. 목표 각도 계산
            target_angle = math.atan2(dy, dx)
            if reverse:
                target_angle += math.pi

            # 2. 부드러운 회전 로직 (Lerp Angle)
            # 현재 각도와 목표 각도 사이의 가장 짧은 차이 계산
            angle_diff = (target_angle - self.angle + math.pi) % (2 * math.pi) - math.pi

            # 회전 속도 제한 (한 프레임에 rotation_speed만큼만 회전)
            if abs(angle_diff) < self.rotation_speed:
                self.angle = target_angle
            else:
                if angle_diff > 0:
                    self.angle += self.rotation_speed
                else:
                    self.angle -= self.rotation_speed

            # 3. 실제 이동 (현재 self.angle 방향으로 직진)
            self.x += math.cos(self.angle) * self.speed
            self.y += math.sin(self.angle) * self.speed

        # 맵 경계 제한
        self.x = max(0, min(MAP_WIDTH, self.x))
        self.y = max(0, min(MAP_HEIGHT, self.y))



    def draw(self, surface, cam_x, cam_y):
        sx, sy = int(self.x - cam_x), int(self.y - cam_y)

        # 1. 이미지 그리기
        if hasattr(self, 'image') and self.image:
            # 현재 각도에 맞춰 이미지 회전
            rotated_img = pygame.transform.rotate(self.image, -math.degrees(self.angle))

            # --- 위치 보정(Offset) 로직 시작 ---
            # TIER_DATA에 offset이 설정되어 있지 않으면 (0, 0) 사용
            data = TIER_DATA[self.tier_idx]
            off_x, off_y = data.get("offset")

            # 캐릭터가 바라보는 각도(self.angle)만큼 오프셋 좌표도 회전시킴
            # (수학적 회전 행렬 공식 적용)
            rotated_off_x = off_x * math.cos(self.angle) - off_y * math.sin(self.angle)
            rotated_off_y = off_x * math.sin(self.angle) + off_y * math.cos(self.angle)

            # 최종 위치 = 원래 중심(sx, sy) + 회전된 보정치
            rect = rotated_img.get_rect(center=(sx + rotated_off_x, sy + rotated_off_y))
            surface.blit(rotated_img, rect.topleft)
            # --- 위치 보정 로직 끝 ---
        else:
            # 이미지가 없으면 기존 방식(색상 원)으로 그리기
            pygame.draw.circle(surface, self.color, (sx, sy), int(self.radius))
            # 입과 꼬리 시각화 (이미지가 없을 때만 표시)
            self._draw_sector(surface, sx, sy, self.angle, (255, 255, 255))
            self._draw_sector(surface, sx, sy, self.angle + math.pi, (0, 0, 0))

        # --- 이름표를 캐릭터 아래에 그리기 ---
        name_font = pygame.font.SysFont("malgungothic", 14, bold=True)

        # 색상 설정
        if not self.is_bot:
            name_color = (255, 255, 0)
        elif self.name == "H_U_N_T_E_R":
            name_color = (255, 50, 50)
        else:
            name_color = (255, 255, 255)

        name_surface = name_font.render(self.name, True, name_color)

        # 위치 계산: 캐릭터 중심(sy) + 반지름(radius) + 여유공간(15)
        # 캐릭터 바로 아래쪽에 이름이 오도록 배치합니다.
        name_rect = name_surface.get_rect(center=(sx, sy + self.radius + 15))

        # 가독성을 위한 검은색 외곽선 효과 (선택 사항: 텍스트가 더 뚜렷해짐)
        shadow_surface = name_font.render(self.name, True, (0, 0, 0))
        surface.blit(shadow_surface, name_rect.move(1, 1))

        surface.blit(name_surface, name_rect)


        # HP 바 표시
        if self.hp < self.max_hp:
            pygame.draw.rect(surface, (255, 0, 0), (sx - 20, sy - self.radius - 10, 40, 5))
            pygame.draw.rect(surface, (0, 255, 0), (sx - 20, sy - self.radius - 10, 40 * (self.hp / self.max_hp), 5))
        if not self.is_bot:  # 플레이어만 에너지 바 표시
            pygame.draw.rect(surface, (100, 100, 100), (sx - 20, sy - self.radius - 4, 40, 3))
            pygame.draw.rect(surface, (0, 255, 255), (sx - 20, sy - self.radius - 4, 40 * (self.energy / 100), 3))

    def _draw_sector(self, surface, sx, sy, center_angle, color):
        points = [(sx, sy)]
        for i in range(-22, 23, 5):
            rad = center_angle + math.radians(i)
            points.append((sx + math.cos(rad) * self.radius, sy + math.sin(rad) * self.radius))
        pygame.draw.polygon(surface, color, points, 2)



# 4. 그 외 사항

# 4-1. 지형 및 먹이 설정 (전역 변수)
ZONE_WIDTH = MAP_WIDTH // 3
SEA_ZONE = (0, ZONE_WIDTH)
LAND_LAVA_ZONE = (ZONE_WIDTH, ZONE_WIDTH * 2)
DESERT_ZONE = (ZONE_WIDTH * 2, MAP_WIDTH)

FOOD_TYPES = {
    "SEA": {"color": (0, 0, 139), "xp": 15},
    "LAND": {"color": (255, 50, 50), "xp": 20},
    "DESERT": {"color": (218, 165, 32), "xp": 50}
}

# 4-2. 먹이 생성 함수
def create_food(zone=None):
    if zone is None:
        zone = random.choice(["SEA", "LAND", "DESERT"])
    if zone == "SEA":
        rx = random.randint(SEA_ZONE[0], SEA_ZONE[1])
    elif zone == "LAND":
        rx = random.randint(LAND_LAVA_ZONE[0], LAND_LAVA_ZONE[1])
    else:
        rx = random.randint(DESERT_ZONE[0], DESERT_ZONE[1])
    ry = random.randint(0, MAP_HEIGHT)
    return {"x": rx, "y": ry, "type": zone}

# 4-3. 초기 먹이 생성
foods = [create_food() for _ in range(300)]


# 4-4. 꼬리 물기
def check_tail_bite(attacker, target):
    dist = math.hypot(attacker.x - target.x, attacker.y - target.y)
    # 두 원이 충분히 겹쳐야 함 (반지름 합의 1.0배 이하로 더 깊게 파고들어야 함)
    if dist > (attacker.radius + target.radius) * 1.0:
        return False

    # 1. 공격자가 타겟을 향한 각도
    angle_to_target = math.atan2(target.y - attacker.y, target.x - attacker.x)

    # 2. 내 정면(입)이 상대를 향하고 있는가? (약 45도 범위)
    atk_diff = (attacker.angle - angle_to_target + math.pi) % (2 * math.pi) - math.pi
    is_mouth_facing = abs(math.degrees(atk_diff)) <= 45

    # 3. [핵심] 내가 상대의 '뒤쪽 반원' 영역에 있는가?
    # 상대의 뒤쪽 180도 영역 어디든 내 입이 닿으면 물림
    target_tail_angle = target.angle + math.pi
    tar_diff = (target_tail_angle - (angle_to_target + math.pi) + math.pi) % (2 * math.pi) - math.pi
    is_touching_back = abs(math.degrees(tar_diff)) <= 45  # 90도 영역 허용

    return is_mouth_facing and is_touching_back

# 4-5. 충돌
def handle_collisions(entities):
    current_time = pygame.time.get_ticks()
    for i, a in enumerate(entities):
        for b in entities[i + 1:]:
            dist = math.hypot(a.x - b.x, a.y - b.y)
            combined_radius = a.radius + b.radius

            if dist < combined_radius:
                overlap = combined_radius - dist

                is_bd_kd_fight = (a.tier_idx >= 8 and b.tier_idx >= 8)

                # 1. 동일 티어 전투 로직 (1v1 도그파이트)
                if a.tier == b.tier or is_bd_kd_fight:
                    # mope.io 스타일: 살짝만 닿아도 각도가 맞으면 물림 (30% 조건 삭제 또는 완화)
                    if overlap > 2:
                        # A가 B를 물었는지 확인
                        if check_tail_bite(a, b):
                            apply_attack(a, b, current_time, 0)
                        # B가 A를 물었는지 확인 (여기서 플레이어인 A가 데미지를 입음)
                        if check_tail_bite(b, a):
                            apply_attack(b, a, current_time, 0)

                    # 동일 티어끼리는 몸을 뚫고 지나갈 수 있게 (밀어내기 생략)
                    continue

                    # 2. 위계 질서가 다를 때 (강자가 약자를 그냥 먹음)
                else:
                    stronger = a if a.tier > b.tier else b
                    weaker = b if a.tier > b.tier else a

                    # 밀어내기 적용 (딱딱한 충돌)
                    nx, ny = (weaker.x - stronger.x) / (dist if dist > 0 else 0.1), (weaker.y - stronger.y) / (
                        dist if dist > 0 else 0.1)
                    weaker.x += nx * overlap
                    weaker.y += ny * overlap

                    # 강자가 약자를 공격
                    apply_attack(stronger, weaker, current_time, 1)

# 4-6 공격, 스킬
def apply_attack(attacker, victim, current_time, is_body_damage= 0):
    # 공격 쿨타임 체크 (2초)
    is_high_tier = min(1, attacker.tier // 8)
    if current_time - attacker.last_attack_time > 2000:
        if attacker.tier == 10:
            damage = 5 + attacker.tier * 3 + (is_body_damage * (20 + is_high_tier * 100))  # 킹드래곤 강함
            victim.hp -= damage
            attacker.last_attack_time = current_time
        else:
            damage = 5 + attacker.tier * 3 + (is_body_damage * (20 + is_high_tier * 50))  # 티어가 높을수록 강함
            victim.hp -= damage
            attacker.last_attack_time = current_time



        # --- 넉백 및 스턴 로직 추가 ---
        angle = math.atan2(victim.y - attacker.y, victim.x - attacker.x)

        # 공격자(attacker)와 피격자(victim) 모두에게 0.2초 스턴 부여
        attacker.stun_timer = 200
        victim.stun_timer = 200

        # 피격자는 뒤로 튕겨나가고, 공격자도 반작용으로 살짝 튕김
        victim.knockback_speed = 5
        victim.knockback_angle = angle

        attacker.knockback_speed = 5
        attacker.knockback_angle = angle + math.pi  # 공격자는 반대 방향

        if victim.hp <= 0:
            # 1. 즉시 XP 획득: 상대방이 다음 진화에 필요한 XP(max_xp)의 50%를 뺏어옴
            reward_xp = victim.max_xp // 2
            attacker.gain_xp(reward_xp)
            # 처치 알림용으로 볼륨을 높여서 한 번 더 재생하거나 다른 소리 출력
            if (not attacker.is_bot or not victim.is_bot) and kill_sound:
                kill_sound.play()
        # 공격 성공 시 경험치 약간 획득, 감소
        attacker.gain_xp(victim.tier * 50 )
        victim.gain_xp(-attacker.tier * 50 )


            


# 4-7 AI 시스템
def run_bot_ai(bot, player, other_bots, foods):
    current_time = pygame.time.get_ticks()

    # 1. 결정 주기가 되었는지 확인
    if current_time - bot.last_ai_update > bot.ai_interval:
        bot.last_ai_update = current_time

        if bot.name == "H_U_N_T_E_R":
            # 결정 주기도 랜덤하게 바꿔주면 봇마다 개성이 생깁니다. ( 원하면 수정 필요 )
            bot.ai_interval = random.randint(100, 200)

            # 주변 상황 파악
            threats, targets, same_tiers = scan_surroundings(bot, player, other_bots)

            # 새로운 상태(Decision) 결정
            if bot.tier_idx <= 4:
                bot.current_decision = "wander"
                bot.target_entity = None

                # 1. 시야 내(view_range)에 있는 먹이들만 필터링
                visible_foods = [f for f in foods if math.hypot(bot.x - f["x"], bot.y - f["y"]) < bot.view_range]

                if visible_foods:
                    # 2. 시야 내 먹이 중 가장 가까운 것 선택
                    closest_food = min(visible_foods, key=lambda f: math.hypot(bot.x - f["x"], bot.y - f["y"]))
                    bot.target_coords = (closest_food["x"], closest_food["y"])
                    bot.is_dashing = True
                else:
                    # 3. 시야 내에 먹이가 없다면, 랜덤한 방향으로 멀리 이동 (새로운 먹이를 찾기 위해)
                    if random.random() < 0.5:  # 너무 자주 바꾸지 않도록 확률 부여
                        bot.target_coords = (
                            random.randint(0, MAP_WIDTH),
                            random.randint(0, MAP_HEIGHT)
                        )

            elif 4 < bot.tier_idx < 7:
                if targets:
                    bot.current_decision = "hunt"
                    closest = min(targets, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                    bot.target_coords = (closest.x, closest.y)
                    bot.is_dashing = True
                elif same_tiers:
                    bot.current_decision = "tail_chase"
                    target_bot = min(same_tiers, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                    bot.target_entity = target_bot  # 이 줄이 반드시 있어야 합니다.

                    # 상대의 꼬리 좌표 계산
                    tail_x = target_bot.x + math.cos(target_bot.angle + math.pi) * target_bot.radius * 0.80
                    tail_y = target_bot.y + math.sin(target_bot.angle + math.pi) * target_bot.radius * 0.80
                    bot.target_coords = (tail_x, tail_y)
                else:
                    bot.current_decision = "wander"
                    bot.target_entity = None

                    # 1. 시야 내(view_range)에 있는 먹이들만 필터링
                    visible_foods = [f for f in foods if math.hypot(bot.x - f["x"], bot.y - f["y"]) < bot.view_range]

                    if visible_foods:
                        # 2. 시야 내 먹이 중 가장 가까운 것 선택
                        closest_food = min(visible_foods, key=lambda f: math.hypot(bot.x - f["x"], bot.y - f["y"]))
                        bot.target_coords = (closest_food["x"], closest_food["y"])
                    else:
                        # 3. 시야 내에 먹이가 없다면, 랜덤한 방향으로 멀리 이동 (새로운 먹이를 찾기 위해)
                        if random.random() < 0.5:  # 너무 자주 바꾸지 않도록 확률 부여
                            bot.target_coords = (
                                random.randint(0, MAP_WIDTH),
                                random.randint(0, MAP_HEIGHT)
                            )

            else:
                if same_tiers:
                    bot.current_decision = "tail_chase"
                    target_bot = min(same_tiers, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                    bot.target_entity = target_bot  # 이 줄이 반드시 있어야 합니다.

                    # 상대의 꼬리 좌표 계산
                    tail_x = target_bot.x + math.cos(target_bot.angle + math.pi) * target_bot.radius * 0.80
                    tail_y = target_bot.y + math.sin(target_bot.angle + math.pi) * target_bot.radius * 0.80
                    bot.target_coords = (tail_x, tail_y)
                    bot.is_dashing = True

                elif targets:
                    bot.current_decision = "hunt"
                    closest = min(targets, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                    bot.target_coords = (closest.x, closest.y)
                    bot.is_dashing = True

                else:
                    bot.current_decision = "wander"
                    bot.target_entity = None

                    # 1. 시야 내(view_range)에 있는 먹이들만 필터링
                    visible_foods = [f for f in foods if math.hypot(bot.x - f["x"], bot.y - f["y"]) < bot.view_range]

                    if visible_foods:
                        # 2. 시야 내 먹이 중 가장 가까운 것 선택
                        closest_food = min(visible_foods, key=lambda f: math.hypot(bot.x - f["x"], bot.y - f["y"]))
                        bot.target_coords = (closest_food["x"], closest_food["y"])
                    else:
                        # 3. 시야 내에 먹이가 없다면, 랜덤한 방향으로 멀리 이동 (새로운 먹이를 찾기 위해)
                        if random.random() < 0.5:  # 너무 자주 바꾸지 않도록 확률 부여
                            bot.target_coords = (
                                random.randint(0, MAP_WIDTH),
                                random.randint(0, MAP_HEIGHT)
                            )
        else:
            # 결정 주기도 랜덤하게 바꿔주면 봇마다 개성이 생깁니다. ( 원하면 수정 필요 )
            bot.ai_interval = random.randint(200, 300)

            # 주변 상황 파악
            threats, targets, same_tiers = scan_surroundings(bot, player, other_bots)

            # 새로운 상태(Decision) 결정
            decision = random.random()
            # 1순위 - 도망
            if threats and decision < 0.5:
                bot.current_decision = "flee"
                closest = min(threats, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                bot.target_coords = (closest.x, closest.y)
            # 2순위 - 1v1
            elif same_tiers and decision < 0.8:
                bot.current_decision = "tail_chase"
                # [수정] target_entity를 실제로 할당해줘야 합니다!
                target_bot = min(same_tiers, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                bot.target_entity = target_bot  # 이 줄이 반드시 있어야 합니다.

                # 상대의 꼬리 좌표 계산
                tail_x = target_bot.x + math.cos(target_bot.angle + math.pi) * target_bot.radius * 0.70
                tail_y = target_bot.y + math.sin(target_bot.angle + math.pi) * target_bot.radius * 0.70
                bot.target_coords = (tail_x, tail_y)

                # [추가 보정] mope.io 스타일의 측면 진입 로직
                if bot.target_entity:  # 한번 더 안전하게 체크
                    t = bot.target_entity
                    side_angle = t.angle + math.pi + math.radians(random.choice([-30, 30]))
                    tx = t.x + math.cos(side_angle) * (t.radius * 0.8)
                    ty = t.y + math.sin(side_angle) * (t.radius * 0.8)
                    bot.target_coords = (tx, ty)
            # 3순위 - 사냥
            elif targets and decision < 0.8:
                bot.current_decision = "hunt"
                closest = min(targets, key=lambda t: math.hypot(bot.x - t.x, bot.y - t.y))
                bot.target_coords = (closest.x, closest.y)
            # 4순위 - 먹이 찾기
            else:
                bot.current_decision = "wander"
                bot.target_entity = None

                # 1. 시야 내(view_range)에 있는 먹이들만 필터링
                visible_foods = [f for f in foods if math.hypot(bot.x - f["x"], bot.y - f["y"]) < bot.view_range]

                if visible_foods:
                    # 2. 시야 내 먹이 중 가장 가까운 것 선택
                    closest_food = min(visible_foods, key=lambda f: math.hypot(bot.x - f["x"], bot.y - f["y"]))
                    bot.target_coords = (closest_food["x"], closest_food["y"])
                else:
                    # 3. 시야 내에 먹이가 없다면, 랜덤한 방향으로 멀리 이동 (새로운 먹이를 찾기 위해)
                    if random.random() < 0.5:  # 너무 자주 바꾸지 않도록 확률 부여
                        bot.target_coords = (
                            random.randint(0, MAP_WIDTH),
                            random.randint(0, MAP_HEIGHT)
                        )


    # 2. 결정된 상태에 따라 실제 이동 (이것은 매 프레임 실행)
    execute_decision(bot)
    avoid_walls(bot)

# 4-8. AI 벽 피하기
def avoid_walls(bot):
    """맵 끝에 도달하면 중앙으로 방향을 틉니다."""
    margin = 100
    if bot.x < margin or bot.x > MAP_WIDTH - margin or bot.y < margin or bot.y > MAP_HEIGHT - margin:
        # 맵의 중앙 좌표
        center_x, center_y = MAP_WIDTH // 2, MAP_HEIGHT // 2
        # 중앙을 향해 조금 더 강한 가중치로 이동하게 유도
        bot.move_towards(center_x, center_y)

# 4-9. AI 주변 파악
def scan_surroundings(bot, player, other_bots):
    """주변의 위협, 타겟, 동급 개체를 리스트로 반환"""
    threats, targets, same_tiers = [], [], []
    for other in [player] + other_bots:
        if other == bot: continue
        dist = math.hypot(bot.x - other.x, bot.y - other.y)
        if dist < bot.view_range:
            if (bot.tier_idx >= 8 and other.tier_idx >= 8):
                same_tiers.append(other)
            elif other.tier > bot.tier:
                threats.append(other)
            elif other.tier < bot.tier:
                targets.append(other)
            else:
                same_tiers.append(other)
    return threats, targets, same_tiers

# 4-10. AI 행동 실행
def execute_decision(bot):
    tx, ty = bot.target_coords
    dist = math.hypot(tx - bot.x, ty - bot.y)

    if bot.current_decision == "tail_chase":
        # 1. 꼬리와의 거리가 아주 가까워지면 (반지름의 1.5배 이내)
        if dist < bot.radius * 1.5 and hasattr(bot, 'target_entity'):
            # 이제 목표 좌표(tx, ty)가 아니라 '상대방 본체 중심'을 바라보도록 각도 정렬
            t = bot.target_entity
            angle_to_center = math.atan2(t.y - bot.y, t.x - bot.x)

            # 부드러운 회전 적용 (입을 상대방 중심으로 고정)
            angle_diff = (angle_to_center - bot.angle + math.pi) % (2 * math.pi) - math.pi
            if abs(angle_diff) < bot.rotation_speed * 0.8:
                bot.angle = angle_to_center
            else:
                bot.angle += bot.rotation_speed * 0.8 if angle_diff > 0 else -bot.rotation_speed

            # 2. 입이 정렬되었고 대시 에너지가 있다면 순간적으로 돌진하여 물기
            if abs(math.degrees(angle_diff)) < 15:  # 15도 이내로 정렬되면
                bot.is_dashing = True
                # 돌진하며 약간 전진
                bot.x += math.cos(bot.angle) * bot.speed
                bot.y += math.sin(bot.angle) * bot.speed
        else:
            if bot != bots[0]:
                bot.is_dashing = False
            bot.move_towards(tx, ty)

    elif bot.current_decision == "flee":
        bot.is_dashing = True if bot.energy > 50 else False
        bot.move_towards(tx, ty, reverse=True)
    else:
        if bot != bots[0]:
            bot.is_dashing = False
        bot.move_towards(tx, ty)

# 순위표 (리더보드)
def draw_leaderboard(surface, player, bots):
    # 1. 모든 개체를 하나의 리스트로 합치고 XP 기준 내림차순 정렬
    all_entities = [player] + bots
    # 정렬 기준: xp (가장 높은 사람이 위로)
    sorted_entities = sorted(all_entities, key=lambda e: e.xp, reverse=True)

    # 2. UI 설정
    font = pygame.font.SysFont("malgungothic", 16, bold=True)
    start_x = SCREEN_WIDTH - 220
    start_y = 20
    line_height = 25

    # 3. 배경 그리기 (반투명 검정색 박스)
    # 10등까지만 표시하므로 높이를 그에 맞춤
    bg_height = min(len(sorted_entities), 10) * line_height + 40
    overlay = pygame.Surface((200, bg_height), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 100))  # R, G, B, Alpha(투명도)
    surface.blit(overlay, (start_x - 10, start_y - 10))

    # 4. 제목 출력
    title = font.render("LEADERBOARD", True, (255, 255, 255))
    surface.blit(title, (start_x, start_y))

    # 5. 1~10등까지 이름과 XP 출력
    for i, ent in enumerate(sorted_entities[:10]):
        # 내 이름(YOU)은 금색으로 표시
        color = (255, 215, 0) if ent.name == "YOU" else (255, 255, 255)

        rank_text = font.render(f"{i + 1}. {ent.name}", True, color)
        xp_text = font.render(f"{int(ent.xp)}", True, color)

        # 텍스트 그리기
        surface.blit(rank_text, (start_x, start_y + 25 + (i * line_height)))
        # XP는 오른쪽 정렬 느낌으로 배치
        surface.blit(xp_text, (start_x + 140, start_y + 25 + (i * line_height)))

# 노래 순환 리스트
playlist = ["fat.io/Ruff_Money.mp3", "fat.io/Windy_Road.mp3"]
current_track_index = 0
def play_next_song():
    global current_track_index
    try:
        pygame.mixer.music.stop()
        pygame.mixer.music.unload()
        pygame.mixer.music.load(playlist[current_track_index])
        pygame.mixer.music.play(0)
        pygame.mixer.music.set_volume(0.4)
        current_track_index = (current_track_index + 1) % len(playlist)

    except Exception as e:
        print(f"음악 로드 실패: {e}")


# 4-11. 초기 생성 💡
player = Entity(MAP_WIDTH // 2, MAP_HEIGHT // 2, 0, is_bot=False)

bots = [Entity(random.randint(0, MAP_WIDTH), random.randint(0, MAP_HEIGHT), random.randint(0, 3), is_bot=True) for _
        in range(15)]

hunter_bot = Entity(random.randint(6000, 9000), random.randint(0, MAP_HEIGHT), 4, is_bot=True) # 처음부터 4단계로 시작
hunter_bot.name = "H_U_N_T_E_R"
bots.insert(0, hunter_bot)





# 메인 루프

music_started = False
last_music_check_time = 0
OUTSIDE_COLOR = (150, 200, 100)  # 맵 바깥 (연두색)
GRID_COLOR = (220, 220, 220)

async def main():
    global music_started
    global last_music_check_time

    # 게임 시작 시점의 시간을 초기값으로 설정
    last_music_check_time = pygame.time.get_ticks()

    # --- [추가] 닉네임 입력 화면 변수 ---
    input_name = ""
    entering_name = True
    input_font = pygame.font.SysFont("malgungothic", 40, bold=True)
    title_font = pygame.font.SysFont("malgungothic", 80, bold=True)
    # 1. 닉네임 입력 루프
    while entering_name:
        screen.fill((30, 30, 30))  # 어두운 배경

        # 안내 문구
        title_surf = title_font.render("FAT.io", True, (255, 180, 0))
        prompt_surf = input_font.render("Enter Your Nickname:", True, (255, 255, 255))
        name_surf = input_font.render(input_name + "|", True, (0, 255, 255))

        screen.blit(title_surf, (SCREEN_WIDTH // 2 - title_surf.get_width() // 2, 200))
        screen.blit(prompt_surf, (SCREEN_WIDTH // 2 - prompt_surf.get_width() // 2, 400))
        screen.blit(name_surf, (SCREEN_WIDTH // 2 - name_surf.get_width() // 2, 500))

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit();
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN:  # Enter 치면 시작
                    if input_name.strip() == "":
                        player.name = "Unnamed"
                    else:
                        player.name = input_name
                    entering_name = False
                elif event.key == pygame.K_BACKSPACE:
                    input_name = input_name[:-1]
                else:
                    # 최대 15자까지만 입력 제한
                    if len(input_name) < 15:
                        input_name += event.unicode

        pygame.display.flip()
        await asyncio.sleep(0)

    cam_x, cam_y = 0, 0
    game_state = "playing"

    while True:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                return

            if event.type == pygame.MOUSEBUTTONDOWN or event.type == pygame.KEYDOWN:
                if not music_started:
                    play_next_song()
                    music_started = True

        screen.fill(OUTSIDE_COLOR)

        mx, my = pygame.mouse.get_pos()

        if game_state == "playing":
            # --- 1. 카메라 및 마우스 좌표 업데이트 ---
            cam_x = player.x - SCREEN_WIDTH // 2
            cam_y = player.y - SCREEN_HEIGHT // 2
            world_mx, world_my = mx + cam_x, my + cam_y




            # --- 5. 그리기 ---
            # 5-1. 지형 배경 그리기 (순서 중요: 배경 -> 그리드 -> 먹이 -> 캐릭터)
            # 바다
            pygame.draw.rect(screen, (30, 144, 255), (SEA_ZONE[0] - cam_x, 0 - cam_y, ZONE_WIDTH, MAP_HEIGHT))
            # 땅/용암
            pygame.draw.rect(screen, (255, 255, 255), (LAND_LAVA_ZONE[0] - cam_x, 0 - cam_y, ZONE_WIDTH, MAP_HEIGHT))
            # 사막
            pygame.draw.rect(screen, (240, 230, 140), (DESERT_ZONE[0] - cam_x, 0 - cam_y, ZONE_WIDTH, MAP_HEIGHT))

            # 그리드 선 (지형 위에 표시)
            grid_size = 100
            for x in range(0, MAP_WIDTH + 1, grid_size):
                pygame.draw.line(screen, GRID_COLOR, (x - cam_x, 0 - cam_y), (x - cam_x, MAP_HEIGHT - cam_y))
            for y in range(0, MAP_HEIGHT + 1, grid_size):
                pygame.draw.line(screen, GRID_COLOR, (0 - cam_x, y - cam_y), (MAP_WIDTH - cam_x, y - cam_y))

            # 5-2. 먹이 그리기 (보완 버전)
            for f in foods:
                # type이 없으면 기본값 "LAND" 사용
                f_type = f.get("type", "LAND")
                color = FOOD_TYPES[f_type]["color"]
                pygame.draw.circle(screen, color, (int(f["x"] - cam_x), int(f["y"] - cam_y)), 10)

            # 5-3. 캐릭터 그리기
            for bot in bots:
                bot.draw(screen, cam_x, cam_y)
            player.draw(screen, cam_x, cam_y)

            # 5-4. 플레이어 전용 하단 UI (XP 바)
            ui_margin = 20
            ui_width = SCREEN_WIDTH - (ui_margin * 2)
            ui_height = 20
            ui_x = ui_margin
            ui_y = SCREEN_HEIGHT - 40  # 화면 바닥에서 약간 위

            # UI 배경 (어두운 회색)
            pygame.draw.rect(screen, (150, 150, 150), (ui_x, ui_y, ui_width, ui_height), border_radius=10)

            # 실제 경험치 (금색/주황색)
            xp_ratio = (player.xp - player.before_xp) / (player.max_xp - player.before_xp)
            pygame.draw.rect(screen, (255, 180, 0), (ui_x, ui_y, ui_width * xp_ratio, ui_height), border_radius=10)

            # 테두리 (선택 사항)
            pygame.draw.rect(screen, (0, 0, 0), (ui_x, ui_y, ui_width, ui_height), 2, border_radius=10)

            # 텍스트 추가 (현재 티어와 XP 수치)
            font = pygame.font.SysFont("malgungothic", 18, bold=True)  # 한글 폰트 설정
            xp_text = font.render(f"Tier {player.tier} | XP: {int(player.xp)} / {player.max_xp}", True, (0, 0, 0))
            screen.blit(xp_text, (ui_x + 10, ui_y - 25))

            # 리더보드 그리기
            draw_leaderboard(screen, player, bots)

            # --- 2. 봇 상태 업데이트 (AI + 물리) ---
            for bot in bots:
                bot.update_stun()  # 스턴 타이머 감소
                if bot.stun_timer == 0:
                    run_bot_ai(bot, player, [b for b in bots if b != bot], foods)
                else:
                    # 스턴 중일 때는 관성 이동
                    bot.x += math.cos(bot.angle) * bot.speed
                    bot.y += math.sin(bot.angle) * bot.speed

                bot.update_energy()
                bot.update_knockback()  # 넉백 적용

            # 대시 여부 결정
            mouse_buttons = pygame.mouse.get_pressed()
            player.is_dashing = True if (mouse_buttons[0] and player.energy > 5) else False

            player.update_stun()
            if player.stun_timer == 0:
                dist_to_mouse = math.hypot(world_mx - player.x, world_my - player.y)
                if dist_to_mouse > 5:
                    player.move_towards(world_mx, world_my)
            else:
                # 스턴 중 관성 이동
                player.x += math.cos(player.angle) * player.speed
                player.y += math.sin(player.angle) * player.speed

            player.update_energy()
            player.update_knockback()

            # --- 4. 충돌 및 먹이 처리 ---
            # 먹이 먹기 로직 통합
            for f in foods[:]:
                eaten = False

                # 1. 플레이어가 먹었을 때
                if math.hypot(player.x - f["x"], player.y - f["y"]) < player.radius:
                    xp_amount = FOOD_TYPES.get(f.get("type", "LAND"), FOOD_TYPES["LAND"])["xp"]
                    player.gain_xp(xp_amount)
                    player.hp = min(player.max_hp, player.hp + 2)
                    player.energy = min(100, player.energy + 20)

                    foods.remove(f)
                    # 먹이가 원래 가진 타입을 유지하며 리스폰, 없으면 무작위
                    foods.append(create_food(f.get("type")))
                    eaten = True

                # 2. 봇들이 먹었을 때 (플레이어가 안 먹었을 경우만 체크)
                if not eaten:
                    for bot in bots:
                        if math.hypot(bot.x - f["x"], bot.y - f["y"]) < bot.radius:
                            xp_amount = FOOD_TYPES.get(f.get("type", "LAND"), FOOD_TYPES["LAND"])["xp"]
                            bot.gain_xp(xp_amount)
                            bot.hp = min(bot.max_hp, bot.hp + 2)

                            foods.remove(f)
                            foods.append(create_food(f.get("type")))
                            break

            # 개체 간 전투/충돌
            all_entities = [player] + bots
            handle_collisions(all_entities)

            # 사망 봇 리스폰 및 먹이 드랍 수정
            for bot in bots[:]:
                if bot.hp <= 0:
                    # 보상 먹이 드랍 시에도 'type'을 부여해서 에러 방지
                    current_zone = "LAND"
                    if bot.x < SEA_ZONE[1]:
                        current_zone = "SEA"
                    elif bot.x > DESERT_ZONE[0]:
                        current_zone = "DESERT"

                    for _ in range(bot.tier * 3):
                        foods.append({
                            "x": bot.x + random.randint(-20, 20),
                            "y": bot.y + random.randint(-20, 20),
                            "type": current_zone  # 타입 추가!
                        })

                    if bot.name == "H_U_N_T_E_R":
                        bot.x = random.randint(6000,9000)
                        bot.y = random.randint(0,MAP_HEIGHT)
                        new_idx = max(0, bot.tier_idx - 1)
                        bot.update_stats(new_idx)
                    else:
                        bot.x = random.randint(0, MAP_WIDTH)
                        bot.y = random.randint(0, MAP_HEIGHT)
                        new_idx = max(0, bot.tier_idx - 5)
                        bot.update_stats(new_idx)






            if player.hp < 0:
                game_state = "game_over"



        elif game_state == "game_over":
            # 게임 오버 화면 그리기
            screen.fill((0, 0, 0))  # 화면을 검게 비우기
            font = pygame.font.SysFont(None, 74)
            text = font.render('GAME OVER - Press R to Restart', True, (255, 0, 0))
            screen.blit(text, (SCREEN_WIDTH // 2 - 400, SCREEN_HEIGHT // 2 - 40))

            #미리 받아온 event리스트 활용
            for event in events:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
                    player.hp = player.max_hp
                    player.x, player.y = MAP_WIDTH // 2, MAP_HEIGHT // 2
                    player.xp = 0
                    tier_num = max(0, player.tier - 5)
                    player.update_stats(tier_num)
                    game_state = "playing"

        if music_started:
            # 1. 노래가 물리적으로 완전히 멈췄는지 확인
            if not pygame.mixer.music.get_busy():
                # 2. 혹시나 아주 짧은 렉 때문에 멈춘 척 하는 건지 확인하기 위해
                # 아주 짧은 딜레이(예: 0.5초)만 주고 바로 다음 곡 재생
                play_next_song()

        pygame.display.flip()
        clock.tick(60)
        # 매 프레임마다 브라우저에게 순서 양보
        await asyncio.sleep(0.01)

# 나중에 항목별로 코드 묶어둘 때 (즉시 실행 에러) 방지용 코드.
if __name__ == "__main__":
    asyncio.run(main())