import discord
from discord.ext import commands
from discord import app_commands
import json
import os

# ─────────────────────────────────────────
#  CONFIGURAZIONE
# ─────────────────────────────────────────
TOKEN = "MTQ4OTA0OTU2NDQ5NjUyNzU1MA.Gbwtjh.KgW_AktG114szt6fzLtnafE-lxD238tqOuGbwI"
CONFIG_FILE = "config.json"

# ─────────────────────────────────────────
#  CARICAMENTO / SALVATAGGIO CONFIG
# ─────────────────────────────────────────
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ─────────────────────────────────────────
#  BOT SETUP
# ─────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

# ─────────────────────────────────────────
#  MODAL ASSENZA
# ─────────────────────────────────────────
class AssenzaModal(discord.ui.Modal, title="📋 Segnala la tua Assenza"):
    motivo = discord.ui.TextInput(
        label="Motivo dell'assenza",
        placeholder="Es. Motivi personali, vacanza, lavoro...",
        style=discord.TextStyle.paragraph,
        max_length=500,
        required=True
    )
    durata = discord.ui.TextInput(
        label="Durata dell'assenza",
        placeholder="Es. 3 giorni, 1 settimana, dal 10 al 15 aprile...",
        style=discord.TextStyle.short,
        max_length=100,
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        config = load_config()
        guild_id = str(interaction.guild.id)

        # Controlla se il canale è stato configurato
        if guild_id not in config or "canale_assenze" not in config[guild_id]:
            await interaction.response.send_message(
                "❌ Il canale per le assenze non è stato configurato! "
                "Un amministratore deve usare `/setup_assenze`.",
                ephemeral=True
            )
            return

        canale_id = config[guild_id]["canale_assenze"]
        canale = interaction.guild.get_channel(canale_id)

        if canale is None:
            await interaction.response.send_message(
                "❌ Il canale configurato non esiste più. Contatta un amministratore.",
                ephemeral=True
            )
            return

        # Embed da inviare nel canale assenze
        embed = discord.Embed(
            title="🚨 Nuova Segnalazione di Assenza",
            color=discord.Color.orange(),
            timestamp=interaction.created_at
        )
        embed.set_author(
            name=interaction.user.display_name,
            icon_url=interaction.user.display_avatar.url
        )
        embed.add_field(name="👤 Membro", value=interaction.user.mention, inline=True)
        embed.add_field(name="⏳ Durata", value=self.durata.value, inline=True)
        embed.add_field(name="📝 Motivo", value=self.motivo.value, inline=False)
        embed.set_footer(text=f"ID: {interaction.user.id}")

        await canale.send(embed=embed)

        # Conferma privata all'utente
        await interaction.response.send_message(
            "✅ La tua assenza è stata segnalata con successo!",
            ephemeral=True
        )


# ─────────────────────────────────────────
#  VIEW CON BOTTONE
# ─────────────────────────────────────────
class AssenzaView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistente anche dopo riavvio

    @discord.ui.button(
        label="Segnala Assenza",
        style=discord.ButtonStyle.primary,
        emoji="📋",
        custom_id="btn_assenza_persistente"
    )
    async def segnala_assenza(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AssenzaModal())


# ─────────────────────────────────────────
#  EVENTO: BOT PRONTO
# ─────────────────────────────────────────
@bot.event
async def on_ready():
    # Registra la view persistente
    bot.add_view(AssenzaView())
    try:
        synced = await tree.sync()
        print(f"✅ Bot online come {bot.user} | Comandi sincronizzati: {len(synced)}")
    except Exception as e:
        print(f"Errore sincronizzazione comandi: {e}")


# ─────────────────────────────────────────
#  COMANDO: /setup_assenze
# ─────────────────────────────────────────
@tree.command(name="setup_assenze", description="Imposta il canale dove verranno inviate le assenze")
@app_commands.describe(canale="Il canale dove inviare le segnalazioni di assenza")
@app_commands.checks.has_permissions(administrator=True)
async def setup_assenze(interaction: discord.Interaction, canale: discord.TextChannel):
    config = load_config()
    guild_id = str(interaction.guild.id)

    if guild_id not in config:
        config[guild_id] = {}

    config[guild_id]["canale_assenze"] = canale.id
    save_config(config)

    embed = discord.Embed(
        title="✅ Configurazione Salvata",
        description=f"Le segnalazioni di assenza verranno inviate in {canale.mention}.",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ─────────────────────────────────────────
#  COMANDO: /pannello_assenze
# ─────────────────────────────────────────
@tree.command(name="pannello_assenze", description="Invia il pannello per segnalare un'assenza in questo canale")
@app_commands.checks.has_permissions(administrator=True)
async def pannello_assenze(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📋 Gestione Assenze",
        description=(
            "Devi assentarti per un periodo?\n\n"
            "Clicca il bottone qui sotto per segnalare la tua assenza, "
            "indicando il **motivo** e la **durata**.\n\n"
            "La tua segnalazione verrà inoltrata agli amministratori."
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="Usa il bottone per aprire il modulo di assenza")

    await interaction.response.send_message(embed=embed, view=AssenzaView())


# ─────────────────────────────────────────
#  GESTIONE ERRORI PERMESSI
# ─────────────────────────────────────────
@setup_assenze.error
@pannello_assenze.error
async def permission_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ Non hai i permessi per usare questo comando (richiesto: Amministratore).",
            ephemeral=True
        )


# ─────────────────────────────────────────
#  AVVIO BOT
# ─────────────────────────────────────────
bot.run(TOKEN)
