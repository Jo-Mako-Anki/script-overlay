// Persona 5 Royal (PC, Steam): reads each text box in the game's memory.
// Taken from the Agent texthooker scripts (libPCAtlus.js + PC_Steam_Persona_5_Royal.js).
// Needs libPCAtlus.js loaded before it (createTable, readString).
function motif(m) { return m.replace(/\s+/g, '').match(/.{2}/g).join(' '); }
function chercher(mod, m) {  // code sections only (r-x): avoids unreadable ranges
    let r = [];
    for (const z of mod.enumerateRanges('r-x')) {
        try { r = r.concat(Memory.scanSync(z.base, z.size, motif(m))); } catch (e) {}
    }
    return r;
}
const mod = Process.enumerateModules().find(m => m.name.toLowerCase().endsWith('.exe')) || Process.enumerateModules()[0];
const table = createTable('P5R');
table[0xa] = '\n';
(function () {
    send({info: 'module ' + mod.name + ' size ' + mod.size});
    const res = chercher(mod, 'C7 ?????? 01012000 ???? ???????? E8');
    if (res.length === 0) { send({error: 'Text routine not found (different game version?)'}); return; }
    const deb = Memory.scanSync(res[res.length - 1].address.sub(0x200), 0x200, motif('CC 48 ???????? 48'));
    if (deb.length === 0) { send({error: 'Text routine not found (2)'}); return; }
    Interceptor.attach(deb[deb.length - 1].address.add(1), {
        onEnter(args) {
            const type = args[2].and(0xFFFF).toUInt32();
            if (type === 3 || type === 4) {  // TEST: record these types (are the choices here?)
                try { send({dbg: type, text: readString(args[1], table)}); } catch (e) {}
                return;
            }
            try { send({text: readString(args[1], table)}); } catch (e) {}
        }
    });
    send({info: 'ready'});
})();
