from ursina import *
from ursina.prefabs.first_person_controller import FirstPersonController
from ursina.shaders import lit_with_shadows_shader
import random

app = Ursina()


#게임 창 설정
window.cog_button.enabled = False
window.fullscreen = True

# 한글 폰트 추가
default_font = 'NanumGothic.ttf'

# 폰트 설정
Text.default_font = default_font

#플레이어
player = FirstPersonController(position = (-3.3039, 0, 37.5857),rotation = (0, 180, 0))
player.speed = 10
health = 100
current_health = 100


hit_overlay = Entity(
            parent=camera.ui,
            model='quad',
            color=color.rgba(255, 0, 0, 150),
            scale=(2, 2),
            position=(0, 0),
            visible=False)

def show_hit_overlay():
    hit_overlay.visible = True
    invoke(Func(hide_hit_overlay), delay=0.2)

def hide_hit_overlay():
    hit_overlay.visible = False






last_hit = time.time()
invincibillity_time = False

#돈
money = 0
money_text = Text(
    parent = camera.ui,
    position = (-0.8,-0.43),
    style= "bold",
    scale = 2,
    text=f"돈 : {money}")

class FireBall(Entity):
    def __init__(self, speed = 50, lifetime=10,**kwargs):
        super().__init__(**kwargs)
        self.speed =  speed
        self.lifetime = lifetime
        self.start = time.time()
        self.world_position += self.forward * 5

    def update(self):
        hit_info = raycast(self.world_position, self.forward, distance=self.speed*time.dt)

        # 레이캐스트가 충돌한 경우
        if hit_info.hit and hit_info.entity in enemies:
            destroy(self)
            hit_info.entity.take_damage(10)  # 적에게 데미지를 입힘
        # 레이캐스트가 충돌하지 않고 발사체의 수명이 만료된 경우
        elif not hit_info.hit and time.time() - self.start < self.lifetime:
            self.world_position += self.forward * self.speed * time.dt
        else:
            destroy(self)


charge_model = Entity(
    parent=player.camera_pivot,
    model="sphere",
    color=color.red,
    scale=0.3,
    position=(0,0,4),
    visible=False,
    shader="unlit_shader")

class ChargedFireBall(Entity):
    def __init__(self,speed=20, lifetime=20, scale = 1 ,**kwargs):
        super().__init__(**kwargs)
        self.speed = speed
        self.lifetime = lifetime
        self.start = time.time()
        self.world_position += self.forward * 3
        self.scale = scale

        self.damage = 5
        if self.scale == 2:
            self.damage = 10
        elif self.scale == 3:
            self.damage = 20

    def update(self):
        # 발사체의 현재 위치
        current_position = self.world_position

        # 적과 충돌 판정
        collided_enemies = [enemy for enemy in enemies if self.intersects(enemy)]

        hit_map = self.intersects(Map)

        hit_ground = current_position.y <= 0 

        # 적과의 충돌 여부 검사
        if collided_enemies or hit_map or hit_ground:
            self.explode()
            destroy(self)
        # 레이캐스트 수행
        else:
            hit_info = raycast(current_position, current_position + self.forward * self.speed * time.dt, distance=self.speed * time.dt)

            # 레이캐스트가 충돌한 경우
            if hit_info.hit:
                self.explode()
                destroy(self)
            # 레이캐스트가 충돌하지 않고 발사체의 수명이 만료된 경우
            elif time.time() - self.start >= self.lifetime:
                self.explode()
                destroy(self)
            else:
                self.world_position = current_position + self.forward * self.speed * time.dt


    def explode(self):
        # 폭발 이펙트 추가 (단순히 색상 변경 및 크기 증가로 표현)
        explosion = Entity(
            model='sphere',
            color=color.orange,
            scale=self.scale,
            position=self.world_position,
            shader="unlit_shader"
        )
        if self.scale < 3:
            explosion.animate_scale(3 * self.scale, duration=0.1)
            # 주변 적에게 데미지
            for enemy in enemies:
                if not enemy.is_empty() and distance(self.world_position, enemy.position) <= self.scale * 2:
                    enemy.take_damage(self.damage)
            destroy(explosion, delay=0.5)
        else:
            explosion.animate_scale(6 * self.scale, duration=0.1)
            # 주변 적에게 데미지
            for enemy in enemies:
                if not enemy.is_empty() and distance(self.world_position, enemy.position) <= self.scale * 4:
                    enemy.take_damage(self.damage)
            destroy(explosion, delay=0.5)


class Weapon(Entity):
    def __init__(self, reload_time=1, max_ammo=4, **kwargs):
        super().__init__(**kwargs)
        self.reload_time = reload_time
        self.max_ammo = max_ammo
        self.current_ammo = max_ammo
        self.last_shot_time = time.time()
        self.reloading = False
        self.reload_start_time = 0
        self.ammo_text = Text(parent=camera.ui, position=(0.4,-0.44), text=f"Ammo: {self.current_ammo}/{self.max_ammo}",scale = 1.5)
        self.charging = False
        self.charge_start_time = 0

    def shoot(self):
        if not self.reloading and not self.charging:
            if self.current_ammo > 0 and time.time() - self.last_shot_time > 0:  # Adjust fire rate as needed
                FireBall(
                    shader="unlit_shader",
                    model="sphere",
                    color=color.red,
                    scale=0.3,
                    position = player.camera_pivot.world_position,
                    rotation = player.camera_pivot.world_rotation
                )
                self.current_ammo -= 1
                self.last_shot_time = time.time()
                print("Shot fired")
            elif self.current_ammo == 0:
                print("Out of ammo, reloading...")
                self.reload()

    def reload(self):
        if not self.reloading and self.current_ammo < self.max_ammo:
            self.animate_rotation_x(480, duration=self.reload_time/2, curve=curve.linear, interrupt="kill")
            self.reloading = True
            self.reload_start_time = time.time()
            print("Reloading")

    def charge_shot(self):
        if not self.reloading and not self.charging:
            self.charging = True
            self.charge_start_time = time.time()
            print("Charging...")
            charge_model.visible = True

    def release_charge_shot(self):
        if self.charging:
            charge_model.visible = False
            charge_duration = time.time() - self.charge_start_time
            charge_scale = 0
            speed = 20
            if charge_duration <= 1:
                charge_scale = 1
                speed = 20
            elif charge_duration <= 3:
                charge_scale = 2
                speed = 5
            else:
                charge_scale = 3
                speed = 3
            ChargedFireBall(
                shader="unlit_shader",
                model="sphere",
                speed=speed,
                color=color.red,
                scale=charge_scale,
                position=player.camera_pivot.world_position,
                rotation=player.camera_pivot.world_rotation,
                charge_time=charge_duration  # 차징 시간 전달
            )
            
            self.charging = False
            print("Charged shot released")

    def update(self):
        if self.reloading:
            if time.time() - self.reload_start_time > self.reload_time:
                self.animate_rotation_x(120, duration=0, curve=curve.linear)
                self.current_ammo = self.max_ammo
                self.reloading = False
                print("Reloaded")
                self.ammo_text.text = f"Ammo: {self.current_ammo}/{self.max_ammo}"
        elif self.current_ammo == 0:
            self.ammo_text.text = f"Ammo: {self.current_ammo}/{self.max_ammo}"
            self.reload()
        else:
            self.ammo_text.text = f"Ammo: {self.current_ammo}/{self.max_ammo}"
        if self.charging:
            charge_duration = time.time() - self.charge_start_time
            if charge_duration <= 1:
                charge_scale = 1
            elif charge_duration <= 3:
                charge_scale = 2
            else:
                charge_scale = 3
            charge_model.scale = charge_scale
            


#맵
Map = Entity(model = "map.obj", scale =7, collider = "mesh",shader = lit_with_shadows_shader, texture = "brick")

sun =  DirectionalLight(rotation = (45,-45,45),shadows=True)

Sky()

#적
class Enemy(Entity):
    def __init__(self,position=(0, 0.7, 7),speed = 1 ,**kwargs):
        super().__init__(**kwargs)
        self.model = 'enemy.fbx'
        self.scale = 0.005
        self.position = position
        self.shader = lit_with_shadows_shader
        self.collider = 'box'
        self.texture = 'enemy.png'
        self.double_sided = True
        self.health = 20
        self.max_health = 20
        self.speed = speed

        #체력바 생성성
        self.health_bar = Entity(
            model='quad',
            color=color.red,
            scale=(3, 0.3, 1),
            position=self.position,
            double_sided=True,
            rotation = self.rotation,
            shader="unlit_shader")

    def take_damage(self, amount):
        self.health -= amount
        self.update_health_bar()
        print(f"{self} hit")
        if self.health <= 0:
            global money
            money += 5
            print("5 money got")

            self.color = color.white

            print("destroying self health bar")

            destroy(self.health_bar)

            print("done")

            print(f"destroying {self}")

            destroy(self)

            print("destroyed")
        else:
            self.animate_hit()

    def animate_hit(self):
        self.color = color.red
        self.texture = None
        invoke(self.revert_color, delay=0.1)

    def revert_color(self):
        self.texture = 'enemy.png'
        self.color = color.white

    def update_health_bar(self):
        self.health_bar.scale_x = (self.health / self.max_health) * 3

    def update(self):
        if player and self and not self.is_empty():
            try:
                self.look_at(player, "forward")
                self.rotation_x = 0
                self.rotation_z = 0
                self.position += self.forward * 100 * self.speed * time.dt  # Adjust speed as needed

                if self.health_bar and not self.health_bar.is_empty():
                    self.health_bar.look_at(player,"forward")
                    self.health_bar.rotation_z = 0
                    self.health_bar.position = self.position + Vec3(0,1,0)

                global last_hit
                global invincibillity_time

                if distance(self.position, player.position) < 3.5 and not invincibillity_time:

                    global current_health
                    current_health -= 10  # Damage to player when enemy hits
                    print(f"hit by {self}")

                    show_hit_overlay()

                    invincibillity_time = True
                    last_hit = time.time()
                    print("invincibillity_time activated")
            except Exception as e:
                print(f"Error in enemy.update: {e}")




# 적들소환
enemies = []
enemy_positions = []
EnemySpeed = 1
# 적 소환 함수
def spawn_enemy():
    global enemy_positions
    attempts = 0
    while attempts < 10:  # 최대 10번 시도
        # 소환할 위치 무작위 선택
        spawn_position = (random.uniform(-39, 39), 0.7, random.uniform(-39, -30))

        # 이미 존재하는 적들과의 거리 비교
        overlapping = False
        for enemy_position in enemy_positions:
            distance = abs(spawn_position[0] - enemy_position[0]) + abs(spawn_position[2] - enemy_position[2])
            if distance < 1:  # 일정 거리 이내에 겹치는 적이 있다면 다음 위치 선택
                overlapping = True
                break

        # 겹치는 적이 없다면 새로운 적 생성
        if not overlapping:
            new_enemy = Enemy(position=spawn_position,speed = EnemySpeed)
            enemies.append(new_enemy)
            enemy_positions.append(spawn_position)
            break
        
        attempts += 1
    
    # 최대 시도 횟수를 넘어갈 경우 강제로 소환
    if attempts == 10:
        new_enemy = Enemy(position=spawn_position)
        enemies.append(new_enemy)
        enemy_positions.append(spawn_position)


# 무기
weapon = Weapon(model="staff.fbx", scale=0.0002, position=player.position, shader=lit_with_shadows_shader, texture="staff.png", double_sided=True)
weapon.z -= 37
weapon.x += 3.8
weapon.y += 1.7
weapon.rotation_x += 120
weapon.rotation_z += 260
weapon.parent = player

#체력바
player_health_bar = Entity(parent = camera.ui, model = "quad", color = color.green, scale = (0.6,0.03), position = (0,-0.45))
health_text = Text(parent = camera.ui, position = (-0.020,-0.44),text=current_health)

death_overlay = Entity(
        parent=camera.ui,
        model='quad',
        color=color.rgba(0, 0, 0, 255),
        scale=(2, 2),
        position=(0, 0),
        visible=False)

death_text = Text(
    parent=camera.ui,
    color = color.red,
    position=(0.0,0.2),
    origin=(0, 0),
    text="사망하였습니다",
    scale = 4,
    visible = False)

restartButton = Text(
    parent=camera.ui,
    position=(0.0,-0.3),
    origin=(0, 0),
    text="다시 시작",
    scale = 3,
    visible = False)

isDeath = False

def restart():
    global isDeath, enemies, current_health, player, money
    print("재시작")
    death_overlay.visible = False
    death_text.visible = False
    restartButton.visible = False
    isDeath = False
    current_health = 100  # 플레이어 체력 초기화
    player.position = (-3.3039, 0, 37.5857)  # 플레이어 위치 초기화
    player.rotation = (0, 180, 0)  # 플레이어 회전 초기화
    money = 0  # 돈 초기화
    weapon.current_ammo = 4

    for enemy in enemies:
        destroy(enemy)
        destroy(enemy.health_bar)
    enemies.clear()  # 적 목록 초기화

    for fireball in scene.entities:
        if isinstance(fireball, FireBall) or isinstance(fireball, ChargedFireBall):
            destroy(fireball)

def death_screen():
    global isDeath
    isDeath = True
    death_overlay.visible = True
    death_text.visible = True
    restartButton.visible = True


def input(key):
    global isDeath
    if key == "left mouse down" and not isDeath: #발사
        weapon.shoot()
    if key == "r": #장전
        weapon.reload()
    if key == "right mouse down":  # 차징 시작
        weapon.charge_shot()
    if key == "right mouse up":  # 차징 발사
        weapon.release_charge_shot()
    if key == "m":
        print(player.position)
    if key == "b":
        global current_health
        current_health -= 10
    if key == "q":
        global money
        money += 30
    if key == "left mouse down" and isDeath:
        print("재시작하기")
        restart()

spawn_cooldown = 2
last_spawn_time = time.time()

def update():
    global last_spawn_time
    global spawn_cooldown
    global EnemySpeed
    current_time = time.time()
    if money == 0:
        spawn_cooldown = 2
        EnemySpeed = 1
    elif 30 <= money < 60:
        spawn_cooldown = 0.5
    if 60 <= money < 90:
        spawn_cooldown = 0.2
    if money >= 90:
        spawn_cooldown = 0.05
        EnemySpeed = 10


    if current_time - last_spawn_time >= spawn_cooldown:
        spawn_enemy()
        last_spawn_time = current_time

    for enemy in enemies:
        enemy.update()

    player_health_bar.scale_x = ((current_health/health)) * 0.6
    health_text.text = current_health

    money_text.text=f"돈 : {money}"


    global invincibillity_time
    global last_hit
    if invincibillity_time and time.time() - last_hit >=2:
        print("invincibillity_time deactivated")
        invincibillity_time = False

    if current_health <=0:
        death_screen()

app.run()