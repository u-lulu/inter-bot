import discord # pip install py-cord
import json
import re
import random as rnd
from datetime import datetime
from datetime import date
import time
import os
import io
import math
import rolldice # pip install py-rolldice
from func_timeout import func_timeout, FunctionTimedOut # pip install func-timeout
from copy import deepcopy
import asyncio

def log(msg):
	msg = msg.strip()
	print(date.today(), datetime.now().strftime("| %H:%M:%S |"), msg)

log("Initializing...")

bot = discord.Bot(activity=discord.Game(name='Loading...'),status=discord.Status.dnd)

log("Loading token")
token_file = open('token.json')
token_file_data = json.load(token_file)
ownerid = token_file_data["owner_id"]
token = token_file_data["token"]
token_file.close()

num_to_die = {
	1: "1️⃣",
	2: "2️⃣",
	3: "3️⃣",
	4: "4️⃣",
	5: "5️⃣",
	6: "6️⃣"
}

type_to_symbol = {
	'light': '💛',
	'dark': '💔',
	'mastery': '💚',
	'heart': '💙',
	'none': 'flat'
}

log("Defining helper functions")
def d6():
	return rnd.randint(1,6)

def remove_duplicates(lst):
	return list(set(lst))

log("Loading user character data...")
character_data = {}

async def save_character_data(userid=None):
	if userid is None: #fallback to saving all data
		log("Saving all character data...")
		for userid in character_data:
			await save_character_data(userid)
		return
	
	try:
		if userid in character_data:
			psavestart = time.time()
			if not os.path.exists('playerdata'):
				os.mkdir('playerdata')
			with open(f"playerdata/{userid}.json", "w") as outfile:
				outfile.write(json.dumps(character_data[userid],indent=2))
			psaveend = time.time()
			savetime = round(psaveend-psavestart,5)
			this_guys_chars = len(character_data[userid]['chars'])
			sz = os.stat(f"playerdata/{userid}.json").st_size
			size_in_kb = round(sz / (1024), 2)
			size_in_mb = round(sz / (1024*1024), 2)
			log(f"Character data for {userid} saved in {savetime if savetime > 0 else '<0.00001'}s ({size_in_kb if size_in_mb < 1 else size_in_mb} {'KB' if size_in_mb < 1 else 'MB'}). Contains {this_guys_chars} characters.")
		else:
			if os.path.exists(f'playerdata/{userid}.json'):
				log(f"Character data for {userid} deleted.")
				os.remove(f'playerdata/{userid}.json')
	except Exception as e:
		log(f"PLAYER DATA SAVING FOR {userid} THREW AN ERROR: {e}")
		await bot.wait_until_ready()
		owner_object = await bot.get_or_fetch_user(ownerid)
		await owner_object.send(f"**An error occurred while saving `{userid}.json`!**\n```{e}```")

if os.path.exists('playerdata'):
	present_files = os.listdir('playerdata')
	for filename in present_files:
		userid = filename.split(".")[0]
		ploadstart = time.time()
		file = open(f'playerdata/{filename}')
		character_data[userid] = json.load(file)
		file.close()
		ploadend = time.time()
		loadtime = round(ploadend-ploadstart,5)
		this_guys_chars = len(character_data[userid]['chars'])
		sz = os.stat(f'playerdata/{filename}').st_size
		size_in_kb = round(sz / (1024), 2)
		size_in_mb = round(sz / (1024*1024), 2)
		log(f"Loaded player data for {userid} in {loadtime if loadtime > 0 else '<0.00001'}s ({size_in_kb if size_in_mb < 1 else size_in_mb} {'KB' if size_in_mb < 1 else 'MB'}). Contains {this_guys_chars} characters.")
else:
	log("Player data does not exist. Using empty data.")
	os.mkdir('playerdata')

log("Creating generic commands")
@bot.event
async def on_ready():
	await bot.change_presence(activity=discord.Game(name='Interstitial'),status=discord.Status.online)
	log(f"{bot.user} is ready and online in {len(bot.guilds)} guilds!")

@bot.event
async def on_application_command(ctx):
	args = []
	if ctx.selected_options is not None:
		for argument in ctx.selected_options:
			args.append(f"{argument['name']}:{argument['value']}")
	args = ' '.join(args)
	if len(args) > 0:
		log(f"/{ctx.command.qualified_name} {args}")
	else:
		log(f"/{ctx.command.qualified_name}")

@bot.event
async def on_application_command_error(ctx, e):
	await ctx.respond(f"This command could not be fulfilled due to the following error:\n`{e}`")
	raise e

@bot.command(description="Shuts down the bot. Will not work unless you own the bot.")
async def shutdown(ctx):
	if ctx.author.id == ownerid:
		log(f"Shutdown request accepted ({ctx.author.id})")
		await ctx.defer()
		await bot.change_presence(activity=discord.Game(name='Shutting down...'),status=discord.Status.dnd)
		await save_character_data()
		await ctx.respond(f"Restarting.")
		await bot.close()
	else:
		log(f"Shutdown request denied ({ctx.author.id})")
		await ctx.respond(f"Only <@{ownerid}> may use this command.",ephemeral=True)

def get_active_name(ctx):
	uid = None
	cid = None
	try:
		uid = str(ctx.author.id)
		cid = str(ctx.channel_id)
	except:
		uid = str(ctx.interaction.user.id)
		cid = str(ctx.interaction.channel.id)
	if uid in character_data:
		your_actives = character_data[uid]['active']
		if cid in your_actives:
			return your_actives[cid]
	return None

def get_active_char_object(ctx):
	name = get_active_name(ctx)
	if name == None:
		return None
	else:
		uid = None
		try:
			uid = str(ctx.author.id)
		except:
			uid = str(ctx.interaction.user.id)
		return character_data[uid]['chars'][name]

async def roll_with_skill(ctx, extra_mod, advantage, stat, use_links=False):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	await ctx.defer()
	
	inherent_bonus = 0 if stat == 'none' else (character[stat.lower()] if not use_links else min(4,len(character['links'][stat.lower()])))
	if stat == 'none':
		use_links = False
	modifier = inherent_bonus + extra_mod
	
	results = [d6(), d6()]
	if advantage:
		results.append(d6())
	
	dice_string = ""
	for d in results:
		dice_string += " " + num_to_die[d]
	dice_string = dice_string.strip()
	
	sorted_results = sorted(results)
	if advantage:
		results = sorted_results[-2:]
	
	total = sum(results) + modifier
	
	message = f"**{name.upper()}** rolling with {stat.title()}{' links' if use_links else ''}:\n> "
	
	if extra_mod != 0:
		message += f"({dice_string}) {'+' if inherent_bonus >= 0 else '-'} {abs(inherent_bonus)} ( {type_to_symbol[stat.lower()]}{'⛓️' if use_links else ''} ) {'+' if extra_mod >= 0 else '-'} {abs(extra_mod)} ({'bonus' if extra_mod >= 0 else 'penalty'}) = **{total}**: "
	else:
		message += f"({dice_string}) {'+' if inherent_bonus >= 0 else '-'} {abs(inherent_bonus)} ( {type_to_symbol[stat.lower()]}{'⛓️' if use_links else ''} ) = **{total}**: "
	
	save_necessary = False

	if total <= 6:
		message += "You **fail** in what you're attempting."
		character['xp'] += 1
		save_necessary = True
		level_change = 0
		while character['xp'] >= 5:
			level_change += 1
			character['xp'] -= 5
		while character['xp'] < 0:
			level_change -= 1
			character['xp'] += 5
		character['level'] += level_change

		message += f"\n{name.upper()} has gained 1 Experience."
		if level_change > 1:
			message += f"\n**💖 They have gained {level_change} advancements!**"
		elif level_change == 1:
			message += f"\n**💖 They have gained an advancement!**"
		elif level_change == -1:
			message += f"\n**💔 They have lost an an advancement.**"
		elif level_change < -1:
			message += f"\n**💔 They have lost {abs(level_change)} advancements.**"
		message += f"\nTheir Experience track is now at **{character['xp']}/5**.\nThey have {character['level']} advancements."
	elif total <= 9:
		message += "You **partially succeed** in what you're attempting."
	else:
		message += "You **succeed** in what you're attempting."
		if stat != 'none':
			links_reinstated = []
			for link in character['links'][stat.lower()]:
				if link['spent'] and link['locked']:
					link['spent'] = False
					links_reinstated.append(link['name'])
			if len(links_reinstated) > 0:
				message += "\nThe following links have been restored:"
				for l in links_reinstated:
					message += f"\n- {l}"
				save_necessary = True
			
	await ctx.respond(message)
	if save_necessary:
		await save_character_data(str(ctx.author.id))

async def character_names_autocomplete(ctx: discord.AutocompleteContext):
	uid = str(ctx.interaction.user.id)
	if uid in character_data:
		return list(character_data[uid]['chars'].keys())
	else:
		return []
	
@bot.command(description="Create a new character to manage")
async def create_character(ctx, name: discord.Option(str, "The character's name, used for selecting them with other commands.",required=True, max_length=50)):
	userid = str(ctx.author.id)
	
	if userid not in character_data:
		character_data[userid] = {
			"active": {},
			"chars": {}
		}
	
	name = name.lower()
	if name in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the name '{name}'.",ephemeral=True)
		return

	await ctx.defer()
	
	character_data[userid]["chars"][name] = {
		"playbook": None,
		"pronouns": None,
		"harm": 0,
		"xp": 0,
		"level": 0,
		"dark": 0,
		"light": 0,
		"mastery": 0,
		"heart": 0,
		"moves": [],
		"items": [],
		"links": {
			"light": [],
			"dark": [],
			"mastery": [],
			"heart": []
		},
		"notes": ""
	}
	
	msg = f"Created character with the name '{name}'."
	msg += f"\nYou now have {len(character_data[userid]['chars'])} characters."
	await ctx.respond(msg)
	await switch_character(ctx, name)
	return

@bot.command(description="Rename an existing character")
async def rename(ctx,
	name: discord.Option(str, "The name of the character to rename.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete),required=True),
	new_name: discord.Option(str, "The new name of the character.",required=True,max_length=50)):
	userid = str(ctx.author.id)

	name = name.lower()
	if userid not in character_data or name not in character_data[userid]['chars']:
		await ctx.respond(f"You have not created a character with the name '{name}'. You can view what characters you've made with `/list`. Check your spelling, or try creating a new one with `/create_character`.",ephemeral=True)
		return
	
	new_name = new_name.lower()
	if new_name in character_data[userid]["chars"]:
		await ctx.respond(f"You have already created a character with the name '{new_name}'.",ephemeral=True)
		return
	
	await ctx.defer()
	
	character_data[userid]['chars'][new_name] = deepcopy(character_data[userid]['chars'][name])
	del character_data[userid]['chars'][name]
	
	msg = f"Renamed the character **{name.upper()}** to **{new_name.upper()}**."
	character_data[userid]
	for key in character_data[userid]['active']:
		if character_data[userid]['active'][key] == name:
			character_data[userid]['active'][key] = new_name
	await ctx.respond(msg)
	await save_character_data(str(ctx.author.id))

@bot.command(description="Delete a character from your roster")
async def delete_character(ctx, name: discord.Option(str, "The character's name, used for selecting them with other commands.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True)):
	name = name.lower()
	yourid = str(ctx.author.id)
	if yourid not in character_data:
		await ctx.respond("You do not have any character data to delete.",ephemeral=True)
		return
	yourstuff = character_data[yourid]
	if name not in yourstuff['chars']:
		await ctx.respond(f"You do not have a character named '{name}' to delete.",ephemeral=True)
		return
	else:
		await ctx.defer()
		class DeleteConfirm(discord.ui.View):
			@discord.ui.button(label="Cancel deletion", style=discord.ButtonStyle.green, emoji="🔙")
			async def stop_deletion_callback(self, button, interaction):
				if interaction.user.id == ctx.author.id:
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					log(f"Cancelling deletion")
					await ctx.respond(f"Character deletion cancelled.")
				else:
					log("Denying invalid deletion response")
					await interaction.response.send_message("This is not your character deletion prompt.",ephemeral=True)
			@discord.ui.button(label=f"Confirm deletion of {name.upper()}", style=discord.ButtonStyle.red, emoji="🗑️")
			async def accept_deletion_callback(self, button, interaction):
				if interaction.user.id == ctx.author.id:
					deletion_target = name.lower()
					self.disable_all_items()
					await interaction.response.edit_message(view=self)
					log("Confirming deletion")
					message = f"<@{yourid}> Successfully deleted **{deletion_target.upper()}**."
					del yourstuff['chars'][deletion_target]
					channel_unbinds = 0
					keys_to_purge = []
					for key in yourstuff['active']:
						if yourstuff['active'][key] == deletion_target:
							channel_unbinds += 1
							keys_to_purge.append(key)
					if channel_unbinds > 0:
						message += f"\nThis action has cleared your active character across {channel_unbinds} channels:"
					for key in keys_to_purge:
						message += f" <#{key}>"
						del yourstuff['active'][key]
					if len(yourstuff['chars']) <= 0:
						del character_data[yourid]
						message += "\nYou no longer have any characters. All data associated with your User ID has been deleted."
					else:
						message += f"\nYou now have {len(yourstuff['chars'])} characters."
					await ctx.respond(message)
					await save_character_data(str(ctx.author.id))
				else:
					log("Denying invalid deletion response")
					await interaction.response.send_message("This is not your character deletion prompt.",ephemeral=True)
		
		await ctx.respond(f"⚠️ **This action will permanently delete your character {name.upper()}, and all data associated with them.\nIt cannot be undone.\nContinue?**",view=DeleteConfirm(timeout=30,disable_on_timeout=True))

@bot.command(description="List all characters you've created")
async def my_characters(ctx):
	yourid = str(ctx.author.id)
	if yourid in character_data and len(character_data[yourid]['chars']) > 0:
		await ctx.defer()
		yourchars = character_data[yourid]['chars']
		msg = f"Characters created by <@{yourid}>:"
		for name in yourchars:
			msg += f"\n- **{name.upper()}**"
		if len(msg) > 2000:
			msg = msg.replace("*","")
			filedata = io.BytesIO(msg.encode('utf-8'))
			await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata, filename='message.txt'))
			log("Sent character list as file")
		else:
			await ctx.respond(msg)
	else:
		await ctx.respond("You haven't created any characters yet.",ephemeral=True)
	
@bot.command(description="Displays your current active character's sheet")
async def sheet(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	await ctx.defer()

	message = f"# {name.upper()}"
	if character['playbook'] is None:
		message += f"\nPlaybook: *Not set.*"
	else:
		message += f"\nPlaybook: {character['playbook']}"

	if character['pronouns'] is None:
		message += f"\nPronouns: *Not set.*"
	else:
		message += f"\nPronouns: {character['pronouns']}"

	message += "\n## __STATS__"
	message += f"\n🩹 Harm: {character['harm']}/4"
	message += f"\n✨ Experience: {character['xp']}/5"
	message += f"\n🎖️ Advancements: {character['level']}"
	message += f"\n💛 Light: {'+' if character['light'] >= 0 else ''}{character['light']}"
	message += f"\n💔 Dark: {'+' if character['dark'] >= 0 else ''}{character['dark']}"
	message += f"\n💚 Mastery: {'+' if character['mastery'] >= 0 else ''}{character['mastery']}"
	message += f"\n💙 Heart: {'+' if character['heart'] >= 0 else ''}{character['heart']}"

	message += "\n## __MOVES__"
	moves_added = 0
	for move in character['moves']:
		moves_added += 1
		n = move['name']
		e = move['effect']
		message += f"\n### **{n}**\n{e}"
	if moves_added <= 0:
		message += "\n*No moves yet.*"

	message += "\n## __LINKS__"
	links_added = 0
	for link_type in character['links']:
		amount = len(character['links'][link_type])
		if amount > 0:
			message += f"\n**{type_to_symbol[link_type.lower()]} {link_type.title()}** ({amount}): "
			list_of_links = []
			for single_link in character['links'][link_type]:
				links_added += 1
				formatted_link = single_link['name']
				if single_link['locked']:
					if single_link['spent']:
						formatted_link += " (🔓)"
					else:
						formatted_link += " (🔒)"
				list_of_links.append(formatted_link)
			message += ", ".join(list_of_links)
	if links_added <= 0:
		message += "\n*No links formed yet.*"
	
	message += "\n## __ITEMS__"
	items_added = 0
	for item in character['items']:
		items_added += 1
		message += f"\n- {item}"
	if items_added <= 0:
		message += "\n*No items yet.*"
	
	if len(message) > 2000:
		filedata = io.BytesIO(message.encode('utf-8'))
		await ctx.respond("The message is too long to send. Please view the attached file.", file=discord.File(filedata, filename=f'{name.lower()}.md'))
	else:
		await ctx.respond(message)

@bot.command(description="Show your active character's inventory")
async def inventory(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	await ctx.defer()
	message = f"**{name.upper()}**'s inventory:"
	if len(character['items']) <= 0:
		message = f"**{name.upper()}** has no items in their inventory."
	else:
		for item in character['items']:
			message += f"\n- {item}"
	if len(message) > 2000:
		message = message.replace("*","").replace("# ","")
		filedata = io.BytesIO(message.encode('utf-8'))
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata, filename='message.txt'))
		log("Sent inventory as file")
	else:
		await ctx.respond(message)

@bot.command(description="Show your active character's moves")
async def moves(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	await ctx.defer()
	message = f"**{name.upper()}**'s moves:"
	moves_added = 0
	for move in character['moves']:
		moves_added += 1
		n = move['name']
		e = move['effect']
		message += f"\n### **{n}**\n{e}"
	if moves_added <= 0:
		message += "\n*No moves yet.*"
	if len(message) > 2000:
		message = message.replace("*","").replace("# ","")
		filedata = io.BytesIO(message.encode('utf-8'))
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata, filename='message.txt'))
		log("Sent moves list as file")
	else:
		await ctx.respond(message)

@bot.command(description="Show the notes field for your active character")
async def view_notes(ctx, hide_output: discord.Option(bool, "Hides the output message from everyone else.", required=False, default=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	note = character['notes']
	if len(note) <= 0:
		await ctx.respond(f"You have not written any notes for **{name.upper()}**.",ephemeral=True)
	else:
		await ctx.defer()
		message = f"Notes for **{name.upper()}**:\n>>> {note}"
		await ctx.respond(message,ephemeral=hide_output)

@bot.command(description="Edit the notes field for your active character")
async def edit_notes(ctx):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	await ctx.defer()
	note = character['notes']

	class NotesModal(discord.ui.Modal):
		def __init__(self, *args, **kwargs) -> None:
			super().__init__(*args, **kwargs)

			self.add_item(discord.ui.InputText(label=f"Notes for '{name.upper()}'",placeholder="Type your notes here.\nLeave this blank to clear notes.",style=discord.InputTextStyle.long,required=False,value=note,max_length=1900))

		async def callback(self, interaction: discord.Interaction):
			log("Updating character notes...")
			character['notes'] = value=self.children[0].value
			await save_character_data(str(ctx.author.id))
			await interaction.response.send_message(f"Notes for {name.upper()} have been {'updated' if len(character['notes']) > 0 else '**cleared**'}.",ephemeral=True)
	
	modal = NotesModal(title=f"Notes editor")
	await ctx.send_modal(modal)

@bot.command(description="Switch which character is active in this channel")
async def switch_character(ctx, name: discord.Option(str, "The name of the character to switch to.", autocomplete=discord.utils.basic_autocomplete(character_names_autocomplete), required=True)):
	userid = str(ctx.author.id)
	if userid not in character_data or len(character_data[userid]['chars']) <= 0:
		await ctx.respond("You have no characters available. Use `/create_character` to make one.",ephemeral=True)
		return
		
	name = name.lower()
	if name not in character_data[userid]["chars"]:
		await ctx.respond(f"You have not created a character with the name '{name}'. You can view what characters you've made with `/list`. Check your spelling, or try creating a new one with `/create_character`.",ephemeral=True)
		return
	else:
		await ctx.defer()
		character_data[userid]['active'][str(ctx.channel_id)] = name
		await ctx.respond(f"Your active character in this channel is now **{name.upper()}**.")
	return

@bot.command(description="Check your current active character")
async def active_character(ctx, show_all: discord.Option(bool, "If TRUE, lists all channels you have active characters in. FALSE by default.", required=False, default=False)):
	if show_all:
		your_actives = character_data[str(ctx.author.id)]['active']
		if len(your_actives) > 0:
			message = f"Your characters are active in the following {len(your_actives)} channels:"
			for channel in your_actives:
				message += f"\n- <#{channel}> -> {your_actives[channel].upper()}"
			if len(message) < 2000:
				await ctx.respond(message,ephemeral=True)
			else:
				await ctx.defer()
				message = f"Your characters are active in the following {len(your_actives)} channels:"
				for channel in your_actives:
					try:
						channel_object = await bot.fetch_channel(int(channel))
						channel_name = channel_object.name
						message += f"\n- #{channel_name} ({channel}) -> {your_actives[channel].upper()}"
					except Exception as e:
						log(f"Could not resolve name of channel {channel}")
						message += f"\n- Unknown channel ({channel}) -> {your_actives[channel].upper()}"
				filedata = io.BytesIO(message.encode('utf-8'))
				await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata, filename='message.txt'))
				log("Sent actives list as file")
		else:
			await ctx.respond(f"You do not have active characters in any channels.",ephemeral=True)
	else:
		name = get_active_name(ctx)
		if name != None:
			await ctx.respond(f"Your active character in this channel is **{name.upper()}**.",ephemeral=True)
		else:
			await ctx.respond(f"You do not have an active character in this channel.",ephemeral=True)

async def item_autocomp(ctx):
	char = get_active_char_object(ctx)
	if char is None:
		return []
	else:
		return char['items']

async def orig_item_autocomp(ctx):
	return [ctx.options['original_item']]

async def link_names_in_category(ctx):
	character = get_active_char_object(ctx)
	if character is None:
		return []
	link_type = ctx.options['link']
	relevant_links = character['links'][link_type]
	out = []
	for l in relevant_links:
		out.append(l['name'])
	return out

@bot.command(description="Add a link to your active character")
async def add_link(ctx,link: discord.Option(str, "The type of link", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		target: discord.Option(str, "The target of your link", required=True, max_length=100),
		locked: discord.Option(bool, "If the link is locked", default=False)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	for existing_link in character['links'][link]:
		if target.lower() == existing_link['name'].lower():
			await ctx.respond(f"{name.upper()} already has a **{link.title()}** link with **{target}**.",ephemeral=True)
			return
	
	await ctx.defer()

	character['links'][link].append({
		"name": target,
		"locked": locked,
		"spent": False
	})

	await ctx.respond(f"{name.upper()} now has a {'Locked ' if locked else ''}**{link.title()}** link with **{target}**.")
	await save_character_data(str(ctx.author.id))

@bot.command(description="Spend a link from your active character")
async def spend_link(ctx,link: discord.Option(str, "The type of link", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		target: discord.Option(str, "The target of the link to be spent", required=True, autocomplete=discord.utils.basic_autocomplete(link_names_in_category))):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	for existing_link in character['links'][link]:
		if target.lower() == existing_link['name'].lower():
			if existing_link['locked']:
				if existing_link['spent']:
					await ctx.respond(f"{name.upper()} has already spent their {link.title()} link with {existing_link['name']}.\nIt can be reactivated by rolling a 10+ with {link.title()}.",ephemeral=True)
					return
				else:
					await ctx.defer()
					existing_link['spent'] = True
					await ctx.respond(f"{name.upper()} has spent their locked {link.title()} link with {existing_link['name']}!\nIt can be reactivated by rolling a 10+ with {link.title()}.")
					await save_character_data(str(ctx.author.id))
					return
			else:
				await ctx.defer()
				character['links'][link].remove(existing_link)
				await ctx.respond(f"{name.upper()} has spent their {link.title()} link with {existing_link['name']}!\nThis link will need to be re-established before it can be used again.")
				await save_character_data(str(ctx.author.id))
				return
	
	await ctx.respond(f"{name.upper()} does not currently have a {link.title()} link with anyone or anything named {target}.",ephemeral=True)
	return

@bot.command(description="Lock one of your active character's links")
async def lock_link(ctx,link: discord.Option(str, "The type of link", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		target: discord.Option(str, "The target of the link to be spent", required=True, autocomplete=discord.utils.basic_autocomplete(link_names_in_category))):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	for existing_link in character['links'][link]:
		if target.lower() == existing_link['name'].lower():
			if existing_link['locked']:
				await ctx.respond(f"{name.upper()} has already locked their {link.title()} link with {existing_link['name']}.",ephemeral=True)
				return
			else:
				await ctx.defer()
				existing_link['locked'] = True
				existing_link['spent'] = False
				await ctx.respond(f"🔒 {name.upper()} has locked their {link.title()} link with {existing_link['name']}!")
				await save_character_data(str(ctx.author.id))
				return
	
	await ctx.respond(f"{name.upper()} does not currently have a {link.title()} link with anyone or anything named {target}.",ephemeral=True)
	return

@bot.command(description="Lock one of your active character's links")
async def unlock_link(ctx,link: discord.Option(str, "The type of link", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		target: discord.Option(str, "The target of the link to be spent", required=True, autocomplete=discord.utils.basic_autocomplete(link_names_in_category))):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	for existing_link in character['links'][link]:
		if target.lower() == existing_link['name'].lower():
			if not existing_link['locked']:
				await ctx.respond(f"{name.upper()}'s {link.title()} link with {existing_link['name']} is not locked.",ephemeral=True)
				return
			else:
				await ctx.defer()
				existing_link['locked'] = False
				existing_link['spent'] = False
				await ctx.respond(f"{name.upper()} has unlocked their {link.title()} link with {existing_link['name']}!")
				await save_character_data(str(ctx.author.id))
				return
	
	await ctx.respond(f"{name.upper()} does not currently have a {link.title()} link with anyone or anything named {target}.",ephemeral=True)
	return

async def orig_target_autocomp(ctx):
	return [ctx.options['original_target']]

@bot.command(description="Edit an link to someone (or something) to your character")
async def edit_link(ctx, link: discord.Option(str, "The type of link", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		original_target: discord.Option(str, "The target of your link", required=True, autocomplete=discord.utils.basic_autocomplete(link_names_in_category)),
		target: discord.Option(str, "The new name for your targeted link", required=True, autocomplete=discord.utils.basic_autocomplete(orig_target_autocomp)),
		locked: discord.Option(bool, "If the link is locked", default=False), spent: discord.Option(bool, "If the link is spent", default=False)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	for i in range(len(character['links'][link])):
		if original_target.lower() == character['links'][link][i]['name'].lower():
			await ctx.defer()
			old_link = character['links'][link][i]
			character['links'][link][i] = {
				"name": target,
				"locked": locked,
				"spent": spent
			}
			await ctx.respond(f"You have edited one of {name.upper()}'s {link.title()} links.\nName: {old_link['name']} -> **{target}**\nLocked: {old_link['locked']} -> **{locked}**\nSpent: {old_link['spent']} -> **{spent}**")
			await save_character_data(str(ctx.author.id))
			return
	await ctx.respond(f"{name.upper()} does not currently have a {link.title()} link with anyone or anything named {original_target}.",ephemeral=True)
	return

@bot.command(description="Add an item your active character")
async def add_item(ctx,item: discord.Option(str, "The item to add", required=True, max_length=100)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	
	if item in character['items']:
		await ctx.respond(f"{name.upper()} is already carrying an item called **{item}**.",ephemeral=True)
		return
	
	await ctx.defer()
	character['items'].append(item)
	
	await ctx.respond(f"**{name.upper()}** has added **{item}** to their inventory.")
	await save_character_data(str(ctx.author.id))

@bot.command(description="Edit an item in your inventory")
async def edit_item(ctx,original_item: discord.Option(str, "The item to replace", required=True, autocomplete=discord.utils.basic_autocomplete(item_autocomp), max_length=100),item: discord.Option(str, "The item to change it to", required=True, autocomplete=discord.utils.basic_autocomplete(orig_item_autocomp), max_length=100)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	
	if original_item not in character['items']:
		await ctx.respond(f"{name.upper()} is not carrying an item called **{original_item}**.",ephemeral=True)
		return
	elif item in character['items']:
		await ctx.respond(f"{name.upper()} is already carrying an item called **{item}**.",ephemeral=True)
		return
	
	await ctx.defer()
	orig_item_index = character['items'].index(original_item)
	character['items'][orig_item_index] = item
	
	await ctx.respond(f"**{name.upper()}** has replaced **{original_item}** with **{item}** in their inventory.")
	await save_character_data(str(ctx.author.id))

@bot.command(description="Remove an item from your active character")
async def remove_item(ctx,item: discord.Option(str, "The item to remove", required=True, autocomplete=discord.utils.basic_autocomplete(item_autocomp), max_length=100)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)
	
	if item not in character['items']:
		await ctx.respond(f"{name.upper()} is not carrying an item called **{item}**.",ephemeral=True)
		return
	
	await ctx.defer()
	character['items'].remove(item)
	
	await ctx.respond(f"**{name.upper()}** has __removed__ **{item}** to their inventory.")
	await save_character_data(str(ctx.author.id))

@bot.command(description="Roll with your active character")
async def roll(ctx,
		attribute: discord.Option(str, "The attribute to use for the roll", required=True, choices=['dark', 'light', 'mastery', 'heart', 'none']),
		roll_with_links: discord.Option(bool, "Roll with links instead of using an attribute score", required=False, default=False),
		modifier: discord.Option(int, "Extra modifiers for the roll", required=False, default=0),
		advantage: discord.Option(bool, "Roll 3d6 and take the best two", required=False, default=False)
		):
	await roll_with_skill(ctx, modifier, advantage, attribute, roll_with_links)

async def attr_num_autocomp(ctx):
	return [0,1,2,-1,-2]

@bot.command(description="Set your active character's playbook")
async def set_playbook(ctx,
		playbook: discord.Option(str, "The playbook's name", required=True),
		light: discord.Option(int, "The playbook's Light score", required=True, autocomplete=discord.utils.basic_autocomplete(attr_num_autocomp)),
		dark: discord.Option(int, "The playbook's Dark score", required=True, autocomplete=discord.utils.basic_autocomplete(attr_num_autocomp)),
		mastery: discord.Option(int, "The playbook's Mastery score", required=True, autocomplete=discord.utils.basic_autocomplete(attr_num_autocomp)),
		heart: discord.Option(int, "The playbook's Heart score", required=True, autocomplete=discord.utils.basic_autocomplete(attr_num_autocomp)),
		):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	charname = get_active_name(ctx)

	await ctx.defer()
	character['playbook'] = playbook
	character['light'] = light
	character['dark'] = dark
	character['mastery'] = mastery
	character['heart'] = heart

	message = f"{charname.upper()}'s playbook is now **{playbook}**.\nTheir new attribute scores are:"
	message += f"\n💛 Light: {'+' if character['light'] >= 0 else ''}{character['light']}"
	message += f"\n💔 Dark: {'+' if character['dark'] >= 0 else ''}{character['dark']}"
	message += f"\n💚 Mastery: {'+' if character['mastery'] >= 0 else ''}{character['mastery']}"
	message += f"\n💙 Heart: {'+' if character['heart'] >= 0 else ''}{character['heart']}"

	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))
	return

sample_pronouns = ["they/them","she/her","he/him","it/its","any pronouns","unspecified pronouns","no pronouns","ae/aer","bun/buns","e/em","ey/em","fae/faer","liv/lir","mer/merm","nya/nyas","pup/pups","shi/hir","sie/hir","v/v","ve/ver","xe/xem","ze/zir"]

async def pronouns_autocomplete(ctx):
	return sample_pronouns

@bot.command(description="Set your active character's pronouns")
async def set_pronouns(ctx,
		pronouns: discord.Option(str, "The pronouns to set", required=True, autocomplete=discord.utils.basic_autocomplete(pronouns_autocomplete), max_length=30)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	charname = get_active_name(ctx)
	await ctx.defer()

	character['pronouns'] = pronouns

	await ctx.respond(f"{charname.upper()} now goes by the pronouns **{pronouns}**.")
	await save_character_data(str(ctx.author.id))
	return

@bot.command(description="Set the value for one of your character's attributes")
async def set_attribute(ctx,
		attribute: discord.Option(str, "The attribute to change", required=True, choices=['dark', 'light', 'mastery', 'heart']),
		new_value: discord.Option(int, "The new value for the attribute", required=True)
		):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	charname = get_active_name(ctx)

	await ctx.defer()
	character[attribute] = new_value

	await ctx.respond(f"{charname.upper()}'s **{type_to_symbol[attribute.lower()]} {attribute.title()}** score is now **{'+' if new_value >= 0 else ''}{new_value}**.")
	await save_character_data(str(ctx.author.id))
	return

@bot.command(description="Add a Move to your active character")
async def add_move(ctx, name: discord.Option(str,"The name of the move.",required=True,max_length=100), effect: discord.Option(str,"The effect of the move.",required=True)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	charname = get_active_name(ctx)

	for move in character['moves']:
			if move['name'].lower() == name.lower():
				await ctx.respond(f"{charname.upper()} already has a move called '{move['name']}'.",ephemeral=True)
				return

	await ctx.defer()
	character['moves'].append({
		'name': name,
		'effect': effect
	})

	await ctx.respond(f"{charname.upper()} has gained a move!\n>>> **{name}**\n{effect}")
	await save_character_data(str(ctx.author.id))
	return

async def current_moves_autocomp(ctx):
	character = get_active_char_object(ctx)
	if character is None:
		return []
	out = []
	for move in character['moves']:
		out.append(move['name'])
	return out

@bot.command(description="Remove a Move from your active character")
async def remove_move(ctx, name: discord.Option(str,"The name of the move to remove.",required=True,autocomplete=discord.utils.basic_autocomplete(current_moves_autocomp))):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	charname = get_active_name(ctx)

	for move in character['moves']:
		if move['name'].lower() == name.lower():
			await ctx.defer()
			character['moves'].remove(move)
			await ctx.respond(f"{charname.upper()} has lost the move **{name}**.")
			await save_character_data(str(ctx.author.id))
			return

	await ctx.respond(f"{charname.upper()} does not have a move named '{name}'.",ephemeral=True)
	return

@bot.command(description="Gain Experience on your active character")
async def experience(ctx, amount: discord.Option(int,"The amount of Experience to gain.",required=False,default=1)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	await ctx.defer()
	character['xp'] += amount
	level_change = 0
	while character['xp'] >= 5:
		level_change += 1
		character['xp'] -= 5
	while character['xp'] < 0:
		level_change -= 1
		character['xp'] += 5
	character['level'] += level_change

	message = f"{name.upper()} has gained {amount} Experience."
	if level_change > 1:
		message += f"\n**💖 They have gained {level_change} advancements!**"
	elif level_change == 1:
		message += f"\n**💖 They have gained an advancement!**"
	elif level_change == -1:
		message += f"\n**💔 They have lost an an advancement.**"
	elif level_change < -1:
		message += f"\n**💔 They have lost {abs(level_change)} advancements.**"
	message += f"\nTheir Experience track is now at **{character['xp']}/5**.\nThey have {character['level']} advancements."
	
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))
	return

@bot.command(description="Apply harm to your active character")
async def harm(ctx, amount: discord.Option(int,"The amount of harm to take.",required=False,default=1,max_value=4,min_value=1)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	await ctx.defer()
	character['harm'] += amount
	if character['harm'] > 4:
		character['harm'] = 4
	dead = character['harm'] >= 4

	message = f"{name.upper()} has taken harm!" if amount == 1 else f"{name.upper()} has taken {amount} harm!"
	message += f"\nTheir harm track is now at **{character['harm']}/4**."

	if dead:
		message += f"\n## {name.upper()} has perished.\nChoose one of the following:\n- You are dead.\n- You relinquish your character to become an NPC.\n- You take a new playbook and start fresh with the same character.\n- You lose all your Links and all marked experience, but can revive later.\n- You owe someone a large favor, and mark them as a Link that is antaganostic to you."
	
	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))
	return

@bot.command(description="Remove harm from your active character")
async def heal(ctx, amount: discord.Option(int,"The amount of harm to remove.",required=False,default=1,max_value=4,min_value=1)):
	character = get_active_char_object(ctx)
	if character == None:
		await ctx.respond("You do not have an active character in this channel. Select one with `/switch_character`.",ephemeral=True)
		return
	name = get_active_name(ctx)

	await ctx.defer()
	character['harm'] -= amount
	if character['harm'] < 0:
		character['harm'] = 0

	message = f"{name.upper()} has healed!" if amount == 1 else f"{name.upper()} has healed {amount} harm!"
	message += f"\nTheir harm track is now at **{character['harm']}/4**."

	await ctx.respond(message)
	await save_character_data(str(ctx.author.id))
	return

log("Creating player commands")
player_group = discord.SlashCommandGroup("player", "Player Commands")

def roll_multiple_dice(syntax, amount):
	out = []
	for i in range(amount):
		out.append(rolldice.roll_dice(syntax))
	return out

@player_group.command(description="Rolls dice using common dice syntax")
async def dice(ctx, syntax: discord.Option(str,"The dice syntax"),
	instances: discord.Option(int, "The number of times to roll this dice formation", required=False, default=1, min_value=1),
	hidden: discord.Option(bool, "If TRUE, the output of this command is hidden to others", required=False, default=False)):
	#log(f"/player dice {syntax} {instances} {hidden}")
	
	timeout = 2
	output = ()
	if instances > 1:
		output = []
	try:
		if instances > 1:
			output = func_timeout(timeout, roll_multiple_dice, args=[syntax,instances])
		else:
			output = func_timeout(timeout, rolldice.roll_dice, args=[syntax])
	except rolldice.rolldice.DiceGroupException as e:
		log(f"Caught: {e}")
		await ctx.respond(f"{e}\nSee [py-rolldice](https://github.com/mundungus443/py-rolldice#dice-syntax) for an explanation of dice syntax.",ephemeral=True)
		return
	except FunctionTimedOut as e:
		log(f"Caught: {e}")
		await ctx.respond(f"It took too long to roll your dice (>{timeout}s). Try rolling less dice.",ephemeral=True)
		return
	except (ValueError, rolldice.rolldice.DiceOperatorException) as e:
		log(f"Caught: {e}")
		await ctx.respond(f"Could not properly parse your dice result. This usually means the result is much too large. Try rolling dice that will result in a smaller range of values.",ephemeral=True)
		return
	
	await ctx.defer()
	message = ""
	if instances > 1:
		strings_to_join = []
		counter = 1
		for item in output:
			strings_to_join.append(f"{counter}. **{item[0]}** (`{item[1]}`)")
			counter += 1
		message = "\n".join(strings_to_join)
	else:
		message = f"**Total: {output[0]}**\n`{output[1]}`"
	if not ('d' in syntax or 'D' in syntax):
		message += f"\n\nIt seems your input didn't actually roll any dice. Did you mean `1d{syntax}` or `{syntax}d6`?\nSee [py-rolldice](<https://github.com/mundungus443/py-rolldice#dice-syntax>) for an explanation of dice syntax."
	
	if len(message) > 2000:
		message = message.replace("*","").replace("`","")
		filedata = io.BytesIO(message.encode('utf-8'))
		await ctx.respond("The message is too long to send. Please view the attached file.",file=discord.File(filedata, filename='message.txt'))
		log("Sent dice results as file")
	else:
		await ctx.respond(message,ephemeral=hidden)

bot.add_application_command(player_group)

log("Starting bot session")
bot.run(token)