#!/usr/bin/perl
use Crypt::PWSafe3

die ($!) unless (-f $ARGV[0] );
die ($!) if (-f $ARGV[1] );

my $vault = Crypt::PWSafe3->new(whoami => 'jmrenouard',  create =>1, file => $ARGV[1], password => $ARGV[2]);
open my $input, $ARGV[0] or die "Could not open $ARGV[0]: $!";
my $group='';
while(my $entries = <$input>) {
	$entries =~ s/^\s+|\s+$//g;
	next if $entries =~/^$/;
	if ($entries =~/^GROUP:/) {
		$group = ($entries =~s/^GROUP://g);
		next;
	}
	my @entry = split(/\t/, $entries);
	$vault->newrecord(	user => $entry[2]. '@'.$entry[1],
						passwd => $entry[4],
						title => $entry[0],
						group => $group,
						notes => 	"Server: ".$entry[0].
									"\nDatabase: ".$entry[1].
									"\nType Acces: ".$entry[2]);
}
$vault->markmodified();
close($input);
$vault->save();
print $vault->getheader('wholastsaved')->value();
print scalar localtime($vault->getheader('lastsavetime')->value());

my $h = Crypt::PWSafe3::HeaderField->new(name => 'savedonhost', value => 'localhost');
$vault->addheader($h);