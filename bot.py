import discord
from discord.ext import commands, tasks
import datetime

# Mengaktifkan intents
intents = discord.Intents.default()
intents.message_content = True
intents.members = True 
bot = commands.Bot(command_prefix='!', intents=intents)

# Variabel konfigurasi
scheduled_message = "Halo! Jangan lupa kerjakan tugasmu."
target_channel_id = None
tagged_users = []      
tagged_user_ids = []   
scheduled_times = [] 
supervisor_user_id = None # Variabel BARU untuk menyimpan ID user kedua (penerima laporan)

# Pengaturan Zona Waktu (WIB = UTC+7)
wib = datetime.timezone(datetime.timedelta(hours=7))

# Membuat Class View untuk Tombol
class TaskView(discord.ui.View):
    def __init__(self, allowed_ids, supervisor_id, bot_instance):
        super().__init__(timeout=None) 
        self.allowed_ids = allowed_ids
        self.supervisor_id = supervisor_id # Mengambil ID user kedua
        self.bot = bot_instance            # Membawa instance bot agar bisa mengirim DM
        self.completed_users = []

    @discord.ui.button(label="Sudah Selesai Makan", style=discord.ButtonStyle.success, custom_id="btn_selesai")
    async def selesai_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        user_id = interaction.user.id
        
        # Validasi apakah yang klik adalah user yang di-tag
        if not self.allowed_ids or user_id in self.allowed_ids:
            if user_id in self.completed_users:
                await interaction.response.send_message("Kamu sudah menceklis tugas ini sebelumnya!", ephemeral=True)
            else:
                self.completed_users.append(user_id)
                # 1. Konfirmasi di channel tempat tombol diklik
                await interaction.response.send_message(f"Horeeee {interaction.user.mention} telah selesai makan!")
                
                # 2. Mengirim DM ke user kedua (Supervisor)
                if self.supervisor_id:
                    supervisor = self.bot.get_user(self.supervisor_id)
                    if supervisor:
                        try:
                            # Teks yang akan dikirim ke DM user kedua
                            pesan_laporan = f"🔔 **Laporan Makan:** {interaction.user.name} Sudah selesai makan:3"
                            await supervisor.send(pesan_laporan)
                        except discord.Forbidden:
                            # Jika user kedua mematikan fitur DM dari server, bot akan melapor di channel
                            await interaction.channel.send(f"⚠️ {interaction.user.mention} sudah selesai, tapi saya tidak bisa mengirim DM ke <@{self.supervisor_id}> karena pengaturan privasinya tertutup.")

        else:
            await interaction.response.send_message("❌ Tombol ini hanya untuk mereka yang di-tag pada tugas ini!", ephemeral=True)

# Task loop untuk mengirim pesan
@tasks.loop(time=datetime.time(hour=0, minute=0, tzinfo=wib))
async def auto_message_task():
    if target_channel_id:
        channel = bot.get_channel(target_channel_id)
        if channel:
            mentions = " ".join(tagged_users)
            final_message = f"{scheduled_message} {mentions}".strip()
            
            # Memasukkan data supervisor ke dalam View tombol
            view = TaskView(allowed_ids=tagged_user_ids, supervisor_id=supervisor_user_id, bot_instance=bot)
            await channel.send(final_message, view=view)

@bot.event
async def on_ready():
    print(f'Bot {bot.user} telah online!')

@bot.command(name="setpesan")
async def set_pesan(ctx, *, pesan: str):
    global scheduled_message
    scheduled_message = pesan
    await ctx.send(f"✅ Pesan otomatis diubah:\n`{pesan}`")

@bot.command(name="settag")
async def set_tag(ctx, *members: discord.Member):
    global tagged_users, tagged_user_ids
    tagged_users = [member.mention for member in members]
    tagged_user_ids = [member.id for member in members]
    
    if tagged_users:
        await ctx.send(f"✅ Bot akan men-tag: {' '.join(tagged_users)}")
    else:
        await ctx.send("✅ Tag dibersihkan.")

# Command BARU: Mengatur siapa user kedua yang menerima notifikasi DM
@bot.command(name="setlapor")
async def set_lapor(ctx, member: discord.Member):
    global supervisor_user_id
    supervisor_user_id = member.id
    await ctx.send(f"✅ Bot akan mengirim DM laporan penyelesaian tugas ke {member.mention}.")

@bot.command(name="setchannel")
async def set_channel(ctx):
    global target_channel_id
    target_channel_id = ctx.channel.id
    await ctx.send(f"✅ Pesan akan dikirim ke: {ctx.channel.mention}")

@bot.command(name="setjam")
async def set_jam(ctx, *jam_list: str):
    if target_channel_id is None:
        await ctx.send("⚠️ Atur channel target dulu menggunakan perintah `!setchannel`")
        return

    global scheduled_times
    scheduled_times.clear()
    
    try:
        for jam in jam_list:
            jam_angka, menit_angka = map(int, jam.split(':'))
            waktu = datetime.time(hour=jam_angka, minute=menit_angka, tzinfo=wib)
            scheduled_times.append(waktu)
            
        auto_message_task.change_interval(time=scheduled_times)
        
        if auto_message_task.is_running():
            auto_message_task.restart()
        else:
            auto_message_task.start()
            
        await ctx.send(f"▶️ Jadwal diaktifkan! Pesan akan dikirim setiap jam: **{', '.join(jam_list)} WIB**.")
    except Exception as e:
        await ctx.send("❌ Format jam salah! Gunakan format HH:MM (contoh: `!setjam 08:00 15:30`).")

@bot.command(name="stop")
async def stop_jadwal(ctx):
    if auto_message_task.is_running():
        auto_message_task.cancel()
        await ctx.send("⏹️ Pesan otomatis dihentikan.")
    else:
        await ctx.send("⚠️ Tidak ada jadwal yang sedang berjalan.")

bot.run('MTU1OTE0MzkzNjE4NDk0NjcwOQ.Glty1Y.v-XAv3Daim7GDT__86wsBn51NDFL06bffSXMZo')