"""
bomb.py - Simple Willie bomb prank game
Copyright 2012, Edward Powell http://embolalia.net
Licensed under the Eiffel Forum License 2.

http://willie.dfbta.net
"""
from willie.module import commands, example, rate, require_owner
from random import choice, randint, randrange, sample
from re import search
import sched
import time
from willie.tools import Identifier
from willie import formatting

# code below relies on colors being at least 3 elements long
colors = ['Red', 'Light_Green', 'Light_Blue', 'Yellow', 'White', 'Black', 'Purple', 'Orange', 'Pink']
sch = sched.scheduler(time.time, time.sleep)
fuse = 120  # seconds
timer = '%d minute' % (fuse / 60) if (fuse % 60) == 0 else ('%d second' % fuse)
bombs = dict()


@commands('bomb')
@rate(600)
@example('.bomb nicky')
def start(bot, trigger):
    """
    Put a bomb in the specified user's pants. They will be kicked if they
     don't guess the right wire fast enough.
    """
    if not trigger.group(3):
        bot.say('Who do you want to bomb?')
        return
    if not trigger.sender.startswith('#'):
        bot.say('You can only bomb someone in a channel.')
        return
    global bombs
    global sch
    target = Identifier(trigger.group(3))
    if target == bot.nick:
        bot.say('You thought you could trick me into bombing myself?!')
        return
    if target.lower() in bombs:
        bot.say('I can\'t fit another bomb in ' + target + '\'s pants!')
        return
    if target == trigger.nick:
        bot.say('%s pls. Bomb a friend if you have to!' % trigger.nick)
        return
    if target.lower() not in bot.privileges[trigger.sender.lower()]:
        bot.say('You can\'t bomb imaginary people!')
        return
    if bot.db.get_nick_value(Identifier(target), 'unbombable'):
        bot.say('I\'m not allowed to bomb %s, sorry.' % target)
        return
    wires = [ colors[i] for i in sorted(sample(xrange(len(colors)), randrange(3,5))) ]
    num_wires = len(wires)
    wires_list = [ formatting.color( str(wire), str(wire) ) for wire in wires ]
    wires_list = ", ".join(wires_list[:-2] + [" and ".join(wires_list[-2:])]).replace('Light_', '')
    wires = [ wire.replace('Light_', '') for wire in wires ]
    color = choice(wires)
    message = 'Hey, %s! I think there\'s a bomb in your pants. %s timer, %d wires: %s. ' \
              'Which wire would you like to cut? (respond with %scutwire color)' \
              % ( target, timer, num_wires, wires_list, bot.config.core.help_prefix or '.' )
    bot.say(message)
    bot.notice("Hey, don't tell %s, but it's the %s wire." % (target, color), trigger.nick)
    code = sch.enter(fuse, 1, explode, (bot, trigger))
    bombs[target.lower()] = (wires, color, code)
    sch.run()


@commands('cutwire')
@example('.cutwire red')
def cutwire(bot, trigger):
    """
    Tells willie to cut a wire when you've been bombed.
    """
    global bombs
    target = Identifier(trigger.nick)
    if target.lower() != bot.nick.lower() and target.lower() not in bombs:
        bot.say('You can\'t cut a wire until someone bombs you, ' + target)
        return
    if not trigger.group(2):
        bot.say('You have to choose a wire to cut.')
        return
    wires, color, code = bombs.pop(target.lower())  # remove target from bomb list
    wirecut = trigger.group(2).rstrip(' ')
    if wirecut.lower() in ('all', 'all!'):
        sch.cancel(code)  # defuse timer, execute premature detonation
        bot.say('Cutting ALL the wires! (You should\'ve picked the %s wire.)' % color)
        kmsg = ('KICK %s %s :^!^!^!BOOM!^!^!^' % (trigger.sender, target))
        bot.write([kmsg])
        alls = bot.db.get_nick_value(target, 'bomb_alls') or 0
        alls += 1
        bot.db.set_nick_value(target, 'bomb_alls', alls)
    elif wirecut.capitalize() not in wires:
        bot.say('That wire isn\'t here, ' + target + '! You sure you\'re picking the right one?')
        bombs[target.lower()] = (wires, color, code)  # Add the target back onto the bomb list,
    elif wirecut.capitalize() == color:
        bot.say('You did it, ' + target + '! I\'ll be honest, I thought you were dead. But nope, you did it. You picked the right one. Well done.')
        sch.cancel(code)  # defuse bomb
        defuses = bot.db.get_nick_value(target, 'bomb_defuses') or 0
        defuses += 1
        bot.db.set_nick_value(target, 'bomb_defuses', defuses)
    else:
        sch.cancel(code)  # defuse timer, execute premature detonation
        bot.say('Nope, wrong wire! Aww, now you\'ve gone and killed yourself. Wow. Sorry. (You should\'ve picked the %s wire.)' % color)
        kmsg = 'KICK %s %s :^!^!^!BOOM!^!^!^' % (trigger.sender, target)
        bot.write([kmsg])
        wrongs = bot.db.get_nick_value(target, 'bomb_wrongs') or 0
        wrongs += 1
        bot.db.set_nick_value(target, 'bomb_wrongs', wrongs)


def explode(bot, trigger):
    target = Identifier(trigger.group(3))
    bot.say('%s pls, you could\'ve at least picked one! Now you\'re dead. You see that? Guts, all over the place.' \
        ' (You should\'ve picked the %s wire.)' % (target, bombs[target.lower()][1]) )
    kmsg = 'KICK %s %s :^!^!^!BOOM!^!^!^' % (trigger.sender, target)
    bot.write([kmsg])
    bombs.pop(target.lower())
    timeouts = bot.db.get_nick_value(target, 'bomb_timeouts') or 0
    timeouts += 1
    bot.db.set_nick_value(target, 'bomb_timeouts', timeouts)


@commands('bombstats')
@example('.bombstats')
@example('.bombstats myfriend')
def bombstats(bot, trigger):
    """
    Get bomb stats for yourself or another user.
    """
    if not trigger.group(2):
        target = Identifier(trigger.nick)
    else:
        target = Identifier(trigger.group(2))
    wrongs = bot.db.get_nick_value(target, 'bomb_wrongs') or 0
    timeouts = bot.db.get_nick_value(target, 'bomb_timeouts') or 0
    defuses = bot.db.get_nick_value(target, 'bomb_defuses') or 0
    alls = bot.db.get_nick_value(target, 'bomb_alls') or 0
    total = wrongs + timeouts + defuses + alls
    # short-circuit if user has no stats
    if total == 0:
        msg = 'Nobody bombed %s yet!' % target
        if target != trigger.nick:
            msg += ' Maybe you should be the first, %s. =3' % trigger.nick
        bot.say(msg)
        return
    wrongs += alls # merely a presentation decision
    # grammar shit
    g_wrongs = 'time' if wrongs == 1 else 'times'
    g_timeouts = 'attempt' if timeouts == 1 else 'attempts'
    g_defuses = 'bomb' if defuses == 1 else 'bombs'
    g_alls = 'was' if alls == 1 else 'were'
    msg = '%s defused %d %s, but failed %d %s and didn\'t even bother with %d %s.' \
           % (target, defuses, g_defuses, wrongs, g_wrongs, timeouts, g_timeouts)
    if alls:
        msg += ' (%d of the failures %s from not giving a fuck and cutting ALL the wires!)' % (alls, g_alls)
    bot.say(msg)


@commands('bombstatreset')
@example('.bombstatreset spammer')
@require_owner('Only the bot owner can reset bomb stats')
def statreset(bot, trigger):
    """
    Reset a given user's bomb stats (e.g. after abuse)
    """
    if not trigger.group(2):
        bot.say('Whose bomb stats do you want me to reset?')
        return
    target = trigger.group(2)
    keys = ['bomb_wrongs', 'bomb_defuses', 'bomb_timeouts', 'bomb_alls']
    for key in keys:
        bot.db.set_nick_value(target, key, 0)
    bot.say('Bomb stats for %s reset.' % target)


@commands('bomboff')
@example('.bomboff')
def exclude(bot, trigger):
    """
    Disable bombing yourself (admins: or another user)
    """
    if not trigger.group(2):
        target = trigger.nick
    else:
        target = Identifier(trigger.group(2))
    if not trigger.admin and target != trigger.nick:
        bot.say('Only bot admins can exclude other users.')
        return
    bot.db.set_nick_value(target, 'unbombable', True)
    bot.say('Marked %s as unbombable.' % target)


@commands('bombon')
@example('.bombon')
def unexclude(bot, trigger):
    """
    Re-enable bombing yourself (admins: or another user)
    """
    if not trigger.group(2):
        target = trigger.nick
    else:
        target = Identifier(trigger.group(2))
    if not trigger.admin and target != trigger.nick:
        bot.say('Only bot admins can unexclude other users.')
        return
    bot.db.set_nick_value(target, 'unbombable', False)
    bot.say('Marked %s as bombable again.' % target)

